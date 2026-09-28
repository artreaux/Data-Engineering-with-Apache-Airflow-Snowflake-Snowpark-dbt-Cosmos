from airflow.operators.dummy_operator import DummyOperator
from astro import sql as aql
from astro.files import File
from astro.sql.table import Table
from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, ExecutionConfig
from cosmos.profiles import SnowflakeUserPasswordProfileMapping
from astronomer.providers.snowflake.utils.snowpark_helpers import SnowparkTable
from pathlib import Path
import os
from datetime import datetime
from airflow.decorators import dag, task

dbt_project_path = Path("/usr/local/airflow/dags/dbt/cosmosproject")
snowflake_objects = {'demo_database': 'DEMO',
                     'demo_schema': 'DEMO',
                     'demo_warehouse': 'COMPUTE_WH',
                     'demo_xcom_stage': 'XCOM_STAGE',
                     'demo_xcom_table': 'XCOM_TABLE',
                     'demo_snowpark_wh': 'SNOWPARK_WH'
}
_SNOWFLAKE_CONN_ID = "snowflake_default"

profile_config = ProfileConfig(
    profile_name="default",
    target_name="dev",
    profile_mapping=SnowflakeUserPasswordProfileMapping(
        conn_id="snowflake_default",
        profile_args={
          "database": "demo_dbt",
            "schema": "public"
        },
    )
)

@dag(default_args={
         "snowflake_conn_id": _SNOWFLAKE_CONN_ID,
         "temp_data_output": "table",
         "temp_data_db": snowflake_objects['demo_database'],
         "temp_data_schema": snowflake_objects['demo_schema'],
         "temp_data_overwrite": True,
         "database": snowflake_objects['demo_database'],
         "schema": snowflake_objects['demo_schema']
         },
    schedule_interval="@daily",
    start_date=datetime(2023, 9, 10),
    catchup=False,
    dag_id="dbt_snowpark",
)
def dbt_snowpark_dag():
    transform_data = DbtTaskGroup(
        group_id="transform_data",
        project_config=ProjectConfig(dbt_project_path),
        profile_config=profile_config,
        execution_config=ExecutionConfig(dbt_executable_path=f"{os.environ['AIRFLOW_HOME']}/dbt_venv/bin/dbt"),
        operator_args={"install_deps": True},
    )

    intermediate = DummyOperator(task_id='intermediate')

    @task.snowpark_virtualenv(python_version='3.', requirements=['snowflake-ml-python==1.0.9',
        '/tmp/astro_provider_snowflake-0.0.0-py3-none-any.whl',],)
    def findbesthotel(snowflake_objects:dict): 
        
        df = snowpark_session.sql("""
            SELECT *
            FROM DEMO_DBT.PUBLIC.THIRTY_DAY_AVG_COST
        """).to_pandas()
        highest_cost_hotel = df[df['COST'] == df['COST'].max()]['HOTEL']

        highest_cost_hotel_str = str(highest_cost_hotel)
        print(highest_cost_hotel)

        return highest_cost_hotel_str
    

    besthotel = findbesthotel(snowflake_objects)
    transform_data >> intermediate >> besthotel

dbt_snowpark_dag = dbt_snowpark_dag()
