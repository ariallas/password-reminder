from dataclasses import dataclass

from loguru import logger
from sqlalchemy import URL, create_engine, delete, select, text
from sqlalchemy.pool import NullPool

from src.config import settings
from src.database import db_sessionmaker
from src.database.models import DBUser


@dataclass
class ExternalDBUser:
    id: str
    fio: str
    group: str
    email: str
    ad_login: str


class ExternalDBSyncer:
    """
    Синхронизирует БД приложения с внешней БД пользователей
    """

    def __init__(self) -> None:
        self._externaldb = ExternalDBClient()

    def test_connection(self) -> None:
        self._externaldb.test_connection()

    async def sync(self) -> None:
        logger.info("Syncing with external DB")

        externaldb_users = self._externaldb.get_users()

        async with db_sessionmaker() as session:
            users_result = await session.scalars(select(DBUser))
            users = {user.externaldb_id: user for user in users_result}

        logger.info(f"Currently {len(users)} users in DB")
        updated_users: list[DBUser] = []

        for externaldb_user in externaldb_users:
            user = users.get(externaldb_user.id)
            if user:
                user.externaldb_fio = externaldb_user.fio
                user.externaldb_group = externaldb_user.group
                user.externaldb_email = externaldb_user.email
                user.ad_login = externaldb_user.ad_login
            else:
                user = DBUser(
                    externaldb_id=externaldb_user.id,
                    externaldb_fio=externaldb_user.fio,
                    externaldb_group=externaldb_user.group,
                    externaldb_email=externaldb_user.email,
                    ad_login=externaldb_user.ad_login,
                )
            updated_users.append(user)

        required_externaldb_ids = [externaldb_user.id for externaldb_user in externaldb_users]
        ids_to_delete = [
            user.externaldb_id
            for user in users.values()
            if user.externaldb_id not in required_externaldb_ids
        ]

        async with db_sessionmaker() as session:
            logger.info(f"Updating/adding {len(updated_users)} users")
            session.add_all(updated_users)
            await session.commit()

            if ids_to_delete:
                logger.info(
                    f"Deleting {len(ids_to_delete)} users that are no longer in external DB"
                )
                delete_result = await session.execute(
                    delete(DBUser).where(DBUser.externaldb_id.in_(ids_to_delete))
                )
                await session.commit()
                logger.info(f"Deleted {delete_result.rowcount} users from DB")

        logger.success("Done syncing with external DB")


class ExternalDBClient:
    """
    Клиент для внешней БД пользователей
    """

    def __init__(self) -> None:
        url_object = URL.create(
            "mssql+pymssql",
            username=settings.externaldb_secrets.user.get_secret_value(),
            password=settings.externaldb_secrets.password.get_secret_value(),
            host=settings.externaldb_secrets.host,
            port=settings.externaldb_secrets.port,
            database=settings.externaldb_database,
        )

        self._engine = create_engine(
            url=url_object,
            echo=settings.debug.enable_sqlalchemy_logs,
            poolclass=NullPool,
        )
        self._groups_to_include = settings.externaldb_group_names_to_include
        self._groups_to_exclude = settings.externaldb_group_names_to_exclude

    def test_connection(self) -> None:
        logger.info("Testing external DB connection")
        with self._engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    def get_users(self) -> list[ExternalDBUser]:
        stmt = text("""
            WITH RecursiveGroups AS (
                SELECT ug.id, ug.FullName, ug.ParentUserGroupId
                FROM dbo.UserGroups ug
                WHERE ug.FullName in :groups_names_to_include
                UNION ALL
                SELECT ug.id, ug.FullName, ug.ParentUserGroupId
                FROM RecursiveGroups rg JOIN dbo.UserGroups ug ON rg.id = ug.ParentUserGroupId
                WHERE ug.FullName NOT IN :groups_names_to_exclude
            )
            SELECT DISTINCT u.id, u1.fio, rg.FullName as GroupName, u.Email, u1.AD
            FROM dbo.Users u
            JOIN RecursiveGroups rg ON u.UserGroupId = rg.Id
            JOIN aggregatetables.dbo.users u1 ON u.Id = u1.userid
            WHERE u.IsDeleted=0 AND u1.AD IS NOT NULL
        """)
        stmt = stmt.bindparams(
            groups_names_to_include=self._groups_to_include,
            # Пустой  список в groups_to_exclude вызвывает ошибку SQL, для этого дефолтное значение
            groups_names_to_exclude=self._groups_to_exclude or [""],
        )

        logger.info("Requesting users from external DB")
        with self._engine.connect() as conn:
            result = conn.execute(stmt)
            users = list(result.all())
        logger.info(f"Pulled {len(users)} users from external DB")

        return [
            ExternalDBUser(
                id=str(user.id),
                fio=str(user.fio),
                group=str(user.GroupName),
                email=user.Email or "",
                ad_login=user.AD,
            )
            for user in users
        ]
