# Сервис уведомлений об истечении сроке действия пароля

## Описание

Сервис:
- Берет информацию о пользователях внешней БД
- Ищет по их УЗ AD срок действия пароля
- Уведомляет пользователя на почту и во внешние порталы, если осталось определенное кол-во дней до истечения

Данные о пользователях кэшируются в БД, чтобы минимизировать хождение в AD.

## Инициализация репозитория

```bash
poetry install
poetry shell
pre-commit install
```

Cоздать файл `.env` по образцу из `.env.example`
Для работы pyright должен быть установлен [Node.js](https://nodejs.org/en/download/package-manager)


## Локальный запуск

Локальный запуск:  

```bash
poetry shell
python -m src.main

# Запуск скриптов (пример):
python -m scripts.purge_db
```

## Деплой

При деплое используются значения переменных из `values.yaml` из корня репозитория.  

Если образ с тегом version уже существует в гитлабе, задеплоится уже существующий образ.  
Если такого образа в гитлабе нет, будет собран новый докер образ и залит в гитлаб.  
Изменения файлов конфигурации так же требуют бампа номера версии.  

При деплое новой версии, не забудьте бампнуть номер версии в `values.yaml`

Деплой:
```bash
# Если нужно обновить vats
ansible-galaxy install -r deploy/requirements.yaml

# Собрать и задеплоить (только среда Прод)
ansible-playbook deploy/playbook.yaml -v -i deploy/inventory_prod.yaml

# Вывести строку для подключения к машине по SSH
ansible all --module-name include_role --args name=va.vats.ssh_connection -i deploy/inventory_prod.yaml

# При тестировании можно использовать дополнительный флаг, который будет ВСЕГДА ПЕРЕЗАПИСЫВАТЬ образ с таким же тегом
ansible-playbook deploy/playbook.yaml -v -i deploy/inventory_prod.yaml -e overwrite_image_tag=true
```
