# Import statements
import psycopg2
import psycopg2.extras
from psycopg2 import sql
import sys
import csv
from config import *

db_connection, db_cursor = None, None

# ---------------------------------------------------------------------
# Database connection, set up, insert
# ---------------------------------------------------------------------

# Write code / functions to set up database connection and cursor here.
def get_connection_and_cursor():
    global db_connection, db_cursor
    if not db_connection:
        try:
            if db_password != "":
                db_connection = psycopg2.connect("dbname = {0} user = {1} password = {2}".format(db_name, db_user, db_password))
                print("Success connecting to database")
            else:
                # note you shouldn't use comma to seperate the argument
                db_connection = psycopg2.connect("dbname = {0} user = {1}".format(db_name, db_user))
                
        except:
            print("Unable to connect to the database. Check server and credentials(config.py).")
            sys.exit(1) #force exit of the program

    if not db_cursor:
        db_cursor = db_connection.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
    
    return db_connection, db_cursor

db_connection, db_cursor = get_connection_and_cursor()


# Write code / functions to create tables with the columns you want and all database setup here.
def set_up_database():
    """ This function helps set up the table with column names. """
####### Note: Use double quotes to make sure the name does not convert to lower case by postgres.

    db_cursor.execute('DROP TABLE IF EXISTS "Sites"')
    db_cursor.execute('DROP TABLE IF EXISTS "States"')
    
    # Table: States. All state names are stored in lower case, alphabetically.
    # Column: 
        # - ID (SERIAL)
        # - Name (VARCHAR up to 40 chars, UNIQUE)
    db_cursor.execute('CREATE TABLE "States" ("ID" SERIAL PRIMARY KEY, "Name" VARCHAR(40) NOT NULL UNIQUE)')
     
    # Table: Sites
    # Column: 
        # - ID (SERIAL)
        # - Name (VARCHAR up to 128 chars, UNIQUE)
        # - Type [e.g. "National Lakeshore" or "National Park"] (VARCHAR up to 128 chars)
        # - State_ID (INTEGER - FOREIGN KEY REFERENCING States)
        # - Location (VARCHAR up to 255 chars)
        # - Description (TEXT)
    db_cursor.execute('CREATE TABLE "Sites" ("ID" SERIAL PRIMARY KEY, "Name" VARCHAR(128) NOT NULL UNIQUE, "Type" VARCHAR(128), "State_ID" INTEGER REFERENCES "States"("ID") NOT NULL, "Location" VARCHAR(255), "Description" TEXT)')
 
    # Save 
    db_connection.commit()
    print("Database: Sites, States have been successfully set up.")


# Write code / functions to deal with CSV files and insert data into the database here.
def insert(connection, cursor, table, data_dict, no_return = True):
    """ Accepts connection and cursor, table name, data dictionary that represents one row, and inserts data into the table."""
    #connection.autocommit = True
    column_names = data_dict.keys()

    if not no_return:
        query = sql.SQL('INSERT INTO "{0}"({1}) VALUES({2}) ON CONFLICT DO NOTHING RETURNING "ID"').format(
            sql.SQL(table),
            sql.SQL(', '). join(map(sql.Identifier, column_names)),
            sql.SQL(', ').join(map(sql.Placeholder, column_names))
        )

    else:
        query = sql.SQL('INSERT INTO "{0}"({1}) VALUES({2}) ON CONFLICT DO NOTHING').format(
            sql.SQL(table),
            sql.SQL(', '). join(map(sql.Identifier, column_names)),
            sql.SQL(', ').join(map(sql.Placeholder, column_names))
        )

    sql_string = query.as_string(connection)
    #print(sql_string)
    cursor.execute(sql_string, data_dict)

    if not no_return:
        print (cursor.fetchone()["ID"])
    



# ---------------------------------------------------------------------
# Helper functions to prepare data to be inserted into database and to query
# ---------------------------------------------------------------------

# pass a state_fullname and return the corresponding ID in table States
def get_state_id(state_fullname):
   state_fullname.lower()
   #query = """SELECT "ID" FROM "States" WHERE "Name" = '{}' """.format(state_fullname)
   query = 'SELECT "ID" FROM "States" WHERE "Name" = %s'
   db_cursor.execute(query, (state_fullname,))
   result = db_cursor.fetchone()
   return result["ID"]


# convert each row in csv into parseable site_dictionary
def get_site_diction(site_list, state_id):
    """ site_list is a list about a particular site that contains(in order): NAME, LOCATION, TYPE, ADDRESS, DESCRIPTION"""
    diction = {}
    diction["Name"] = site_list[0]
    diction["Type"] = site_list[2]
    diction["Location"] = site_list[1]
    diction["Description"] = site_list[4]
    diction["State_ID"] = state_id
    return diction

# query data and print
def search(query, number_of_results = 1):
    db_cursor.execute(query)
    results = db_cursor.fetchall()
    print('--> Result Rows:', len(results))
    for result in results[:number_of_results]:
        print(result)
    
    

# ---------------------------------------------------------------------
# Main Function
# ---------------------------------------------------------------------

# Write code to be invoked here (e.g. invoking any functions you wrote above)
if __name__ == '__main__':
    
    command = None
    search_term = None
    if len(sys.argv) > 1: # command line arguments
        command = sys.argv[1] # first thing after the invoked file
        if len(sys.argv) > 2: # if there's more than one command-line arg
            search_term = sys.arg[2]
    
    # Set up database and create table States and Sites
    if command == 'setup':
        print('setting up database')
        set_up_database()

    elif command == 'insert':
        # Insert all states into table States. 
        ## All state names are in lower case and are alphabetially ordered when stored. 
        
        state_dict = {}
        state_list = ["arkansas", "california", "michigan"]
        state_list = [state.lower() for state in state_list]
        state_list.sort()
        ## Insert
        for state in state_list:
            state_dict["Name"] = state
            insert(db_connection, db_cursor, "States", state_dict)
        print("Insert completed for table States.")


        # Insert all states' sites into table Sites.
        ## Different states' sites are stored in state based alphabetical order. 
        site_dict = {}
        csv_list = ["arkansas.csv", "california.csv", "michigan.csv"]
        csv_list.sort()
        for csvfile in csv_list:
            state_fullname = csvfile.split('.')[0]
            state_id = get_state_id(state_fullname)
            with open(csvfile, 'r') as csv_file:
                reader = csv.reader(csv_file)
                first_row = next(reader) # first row is column name, skip it
                for row in reader:
                    site_dict = get_site_diction(row, state_id)
                    insert(db_connection, db_cursor, "Sites", site_dict)
            print("Insert into table Sites completed for {}.".format(csvfile))  

        db_connection.commit()

    else:
        print('Searching all locations...')
        query = """SELECT "Location" FROM "Sites" """
        all_locations = db_cursor.execute(query)
        search(query)
        
        print('--------------------------------')
        print('Searching all sites containting "beautiful"...')
        query = """SELECT "Name" FROM "Sites" WHERE "Description" ilike '%beautiful%'"""
        beautiful_sites = db_cursor.execute(query)
        search(query)
        
        print('--------------------------------')
        print('Searching total number of sites with type "National Lakeshore"...')
        query = """SELECT COUNT("Name") FROM "Sites" WHERE "Type" = %s """
        db_cursor.execute(query, ("National Lakeshore",))
        natl_lakeshores = db_cursor.fetchone()
        print(natl_lakeshores)
        
        print('--------------------------------')
        print('Searching all sites in Michigan ...')
        query = """SELECT "Sites"."Name" FROM "Sites" INNER JOIN "States" ON ("Sites"."State_ID" = "States"."ID") WHERE "States"."Name" = %s """
        db_cursor.execute(query, ("michigan",))
        michigan_names = db_cursor.fetchall()
        print(len(michigan_names))
        
        print('--------------------------------')
        print('Searching total number of sites in Arkansas ...')
        query = 'SELECT count("Sites"."Name") FROM "Sites" INNER JOIN "States" ON ("Sites"."State_ID" = "States"."ID") WHERE "States"."Name" = %s'
        db_cursor.execute(query, ("arkansas",))
        total_number_arkansas = db_cursor.fetchone()
        print(total_number_arkansas)
