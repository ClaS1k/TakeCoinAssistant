import config
import mysql

from mysql import connector

def sql_query(query):
    connection = mysql.connector.connect(user = config.MYSQL_LOGIN, password = config.MYSQL_PASSWORD, host = config.MYSQL_HOST, port='3306', database='TakeCoinAssistant')
    
    with connection.cursor() as cursor:
        cursor.execute(query)

        result = cursor.fetchall()
        connection.commit()

        return result