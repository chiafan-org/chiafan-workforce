from datetime import datetime, timedelta


def format_age(age: timedelta) -> str:
    hours = age.seconds // 3600
    minutes = (age.seconds % 3600) // 60
    seconds = age.seconds % (3600 * 60)
    if age.days > 0:
        return f'{age.days} days {hours:02d}:{minutes:02d}:{seconds:02d}'
    else:
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
