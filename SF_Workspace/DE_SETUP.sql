USE ROLE SECURITYADMIN;

CREATE OR REPLACE ROLE dbt_DEV_ROLE COMMENT='dbt_DEV_ROLE';
GRANT ROLE dbt_DEV_ROLE TO ROLE SYSADMIN;

CREATE OR REPLACE USER dbt_USER PASSWORD='<PASSWORD>'
	DEFAULT_ROLE=dbt_DEV_ROLE
	DEFAULT_WAREHOUSE=dbt_WH
	COMMENT='dbt User';
    
GRANT ROLE dbt_DEV_ROLE TO USER dbt_USER;

-- Grant privileges to role
USE ROLE ACCOUNTADMIN;

GRANT CREATE DATABASE ON ACCOUNT TO ROLE dbt_DEV_ROLE;

/*---------------------------------------------------------------------------
Next we will create a virtual warehouse that will be used
---------------------------------------------------------------------------*/
USE ROLE SYSADMIN;

--Create Warehouse for dbt work
CREATE OR REPLACE WAREHOUSE dbt_DEV_WH
  WITH WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 120
  AUTO_RESUME = true
  INITIALLY_SUSPENDED = TRUE;

GRANT ALL ON WAREHOUSE dbt_DEV_WH TO ROLE dbt_DEV_ROLE;

GRANT ALL ON DATABASE DEMO_dbt TO ROLE dbt_DEV_ROLE;
GRANT ALL ON SCHEMA DEMO_dbt.PUBLIC TO ROLE dbt_DEV_ROLE;
GRANT ALL ON TABLE DEMO_dbt.PUBLIC.bookings_1 TO ROLE dbt_DEV_ROLE;
GRANT ALL ON TABLE DEMO_dbt.PUBLIC.bookings_2 TO ROLE dbt_DEV_ROLE;
GRANT ALL ON TABLE DEMO_dbt.PUBLIC.customers TO ROLE dbt_DEV_ROLE;
CREATE OR REPLACE DATABASE DEMO_dbt;


CREATE OR REPLACE TABLE DEMO_dbt.PUBLIC.bookings_1 (
    id INTEGER,
    booking_reference INTEGER,
    hotel STRING,
    booking_date DATE,
    cost INTEGER
);
CREATE OR REPLACE TABLE DEMO_dbt.PUBLIC.bookings_2 (
    id INTEGER,
    booking_reference INTEGER,
    hotel STRING,
    booking_date DATE,
    cost INTEGER
);
CREATE OR REPLACE TABLE DEMO_dbt.PUBLIC.customers (
    id INTEGER,
    first_name STRING,
    last_name STRING,
    birthdate DATE,
    membership_no INTEGER
);

SHOW GRANTS TO ROLE dbt_dev_role;

TRUNCATE TABLE bookings_1;
TRUNCATE TABLE customers;
TRUNCATE TABLE bookings_2;




