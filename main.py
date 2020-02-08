from bs4 import BeautifulSoup
import datetime
import json
import re
import requests
import sqlite3
import string

# Settings Explanation:
# Trim:
#   If you choose 50 percent trim, it will trim 50 percent of the seats from the sides evenly,
#       Because the goal is to find seats in the middle/center of the theatre.
#
# Seek days: Amount of days into the future you want to crawl for show times.
#
# Print desired data: for debugging reasons, if this is enabled, you'll see what columns and rows it tried to find.
#
# Movie name and theatre list: You can obtain the accurate names from the URLs while you browse around AMC's website.
#
# theatre_types: It will try to find shows and seats for only the theatre types you choose, types can be found in URLs.
#
# chair_type_filter: If you or anyone you know is disabled, you may remove the 'Companion' and 'Wheelchair' filters.

settings = {
    "trim_columns_percentage": 50,
    "trim_rows_percentage": 75,
    "seek_days": 1,
    "seek_showtimes": True,
    "seek_seats": True,
    "print_desired_data": False,
    "movie_name": 'avengers-endgame-45840',

    "theatre_name_list": {
        "amc-lincoln-square-13",  # 3D
        "amc-empire-25",  # 3D
        "amc-kips-bay-15",  # 3D?
        "amc-fresh-meadows-7",  # 3D
    },

    "theatre_types": {
        "imax3d",
        "imax",
    },
    "chair_type_filter": {
        "NotASeat",
        "Companion",
        "Wheelchair"
    }
}

# SQL Settings ----
table_name = 'showtime_seeker'

db_values = {
    "showtime_id": "INTEGER PRIMARY KEY",
    "movie_name": "TEXT",
    "theatre_name": "TEXT",
    "theatre_type": "TEXT",
    "date": "DATETIME",
    "updated": "DATETIME",
}

# Back-end ----

movie_name = settings['movie_name']
theatre_name_list = list(settings['theatre_name_list'])
theatre_types = list(settings['theatre_types'])
chair_type_filter = list(settings['chair_type_filter'])

today = datetime.date.today()


def date_range():
    # list(str(today + datetime.timedelta(days=i)) for day in range(int(settings['seek_days'])))
    result = []
    for day in range(int(settings['seek_days'] + 1)):
        result.append(str(today + datetime.timedelta(days=day)))
    return result


def key_value_db_extractor():
    result = ''
    for k, v in db_values.items():
        result += k + ' ' + v + ','
    return result[0:-1]


def now():
    return str(datetime.datetime.now())


def create_tables(c):
    return c.execute(
        f'''CREATE TABLE if not exists {table_name} ({key_value_db_extractor()})''')


def insert_row(c, *args):
    insert = f"""INSERT OR REPLACE INTO {table_name} VALUES {args};"""
    c.execute(insert)


def find_str_in_list(str_to_compare, list_to_scan):
    if not isinstance(list_to_scan, (list, tuple)):
        new_list_to_scan = list()
        new_list_to_scan.append(list_to_scan)
        list_to_scan = new_list_to_scan
    for name in list_to_scan:
        if name in str_to_compare:
            return True


def showtime_database(*args):
    conn = sqlite3.connect('amc_showtime_seeker.SQLITE3')
    c = conn.cursor()
    try:
        create_tables(c)
        insert_row(c, *args)
        conn.commit()
    finally:
        conn.close()


def grab_showtime_data(url, show_date):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html5lib')
    showtime_theatres = soup.find_all(class_=re.compile("Showtimes-Theatre"))
    for theatre in showtime_theatres[:1]:
        theatre_shows = theatre.find_all('a')
        # print(theatre)
        theatre_name = theatre.find_all('h2')[0].text.strip()
        for show in theatre_shows:
            show_datetime = show.text.strip()
            show_link = show.get('href')
            if find_str_in_list(show_link, theatre_name_list):
                if find_str_in_list(show_link, movie_name):
                    time_str = str(show_date) + ' ' + show_datetime
                    future_date = str(datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M%p'))
                    showtime_id = show_link.split('/')[-1]
                    theatre_type = show_link.split('/')[-2]
                    print('ADDED:', show_link)
                    showtime_database(showtime_id, movie_name, theatre_name, theatre_type, future_date, now())
            else:
                break


def seek_showtime():
    for date in date_range():
        for theatre_name in theatre_name_list:
            for theatre_type in theatre_types:
                url = f'https://www.amctheatres.com/movies/{movie_name}/showtimes/{movie_name}/{date}/{theatre_name}/{theatre_type}'
                print("Seeking Showtimes:", url)
                grab_showtime_data(url, date)


def str_ends_with_number(string):
    return re.search('\d$', string)


def get_percent_of(percentage, number):
    return (float(number) / 100) * float(percentage)


def trim_list_sides(list_items, trim_value):
    """If the trim value is 10, it will trim 5 chairs from the left and 5 chairs from the right"""
    side_trim = int(trim_value / 2)
    if trim_value < 1:
        return list_items
    return list(list_items)[side_trim:-side_trim]


def row_translator(row_list):
    # Later found out that translating rows is useless because AMC considers empty gaps as rows, so row 6 might be E.
    alphabet_dict = dict(enumerate(string.ascii_uppercase, 1))
    translated_row_list = []
    for item in row_list:
        result = alphabet_dict.get(item)
        translated_row_list.append(result)
    return translated_row_list


def get_column_row_lengths(theatre_data):
    for key, value in theatre_data.items():
        if 'seatingLayout' in key:
            columns_length = value['columns']
            rows_length = value['rows']
            return columns_length, rows_length


def is_desired_seat(theatre_data, desired_columns, desired_rows):
    desired_seats_counter = 0
    seat_ids = []
    for key, seat_data in theatre_data.items():
        if ('seatingLayout' in key
                and str_ends_with_number(key)
                and seat_data['column'] in desired_columns
                and seat_data['row'] in desired_rows
                and seat_data['type'] not in chair_type_filter
                and seat_data['available']):
            # print('----------------')
            desired_seats_counter += 1
            seat_ids.append(seat_data['name'])

    return desired_seats_counter, seat_ids


def get_seats(json_data, theatre_name, theatre_type, date):
    theatre_data = json.loads(json_data)

    try:
        columns_length, rows_length = get_column_row_lengths(theatre_data)
    except TypeError:
        print('Showtime no longer available.')
        return

    columns = list(range(1, columns_length + 1))
    rows = list(range(1, rows_length + 1))

    columns_to_trim = get_percent_of(settings['trim_columns_percentage'], columns_length)
    desired_columns = trim_list_sides(columns, columns_to_trim)

    rows_to_trim = get_percent_of(settings['trim_rows_percentage'], rows_length)
    desired_rows = trim_list_sides(rows, rows_to_trim)

    if settings['print_desired_data']:
        print('Desired Columns:', desired_columns)
        print('Desired Rows:', desired_rows)

    desired_seats_counter, seat_ids = is_desired_seat(theatre_data, desired_columns, desired_rows)

    if desired_seats_counter:
        print('Found', desired_seats_counter,
              'seats' if desired_seats_counter > 1 else 'seat', seat_ids)
        print(theatre_name, theatre_type, date)
        print()


def seek_seats(*args):
    conn = sqlite3.connect('amc_showtime_seeker.SQLITE3')
    c = conn.cursor()
    try:
        create_tables(c)
        get_ids = f"""SELECT * FROM {table_name}"""
        c.execute(get_ids)

        results = c.fetchall()
        if results:
            for result in results:
                showtime_id, movie_name, theatre_name, theatre_type, date, updated = result
                url = f"""https://www.amctheatres.com/movies/{movie_name}/showtimes/{movie_name}/{date.split(" ")[
                    0]}/theatre_name/{theatre_type}/{showtime_id}"""
                print('Seeking Seats:', url)
                r = requests.get(url)
                soup = BeautifulSoup(r.content, 'html5lib')
                theatre_json_data = soup.find('script', attrs={'id': 'apollo-data'})

                get_seats(theatre_json_data.text, theatre_name, theatre_type, date)
        else:
            print('There are no showtimes in the database, you must first enable seek_showtimes in the settings')

    finally:
        conn.commit()
        conn.close()


if settings['seek_showtimes']:
    seek_showtime()

if settings['seek_seats']:
    seek_seats()
