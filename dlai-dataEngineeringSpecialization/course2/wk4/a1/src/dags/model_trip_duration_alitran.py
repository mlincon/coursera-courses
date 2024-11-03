import os
from datetime import datetime
from pathlib import Path

import great_expectations as gx
import numpy as np
import pandas as pd
# DAG and task decorators for interfacing with the TaskFlow API
from airflow.decorators import (
    dag,
    task,
)
from airflow.models import Variable
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import BranchPythonOperator
from great_expectations_provider.operators.great_expectations import (
    GreatExpectationsOperator,
)
from scipy.stats import linregress


@dag(
    schedule_interval="@daily",
    start_date=datetime(2022, 1, 1),
    catchup=False,
    default_args={
        "retries": 2,  # If the task fails, it will retry n times
    },
    tags=["dynamic_dag__model_train"],
)
def model_trip_duration_alitran():
    """### Building an advanced data pipeline with data quality checks (Google Composer)
    This is a pipeline to train and deploy a model based on performance.
    """
    vendor_name = "alitran"
    start_task = DummyOperator(task_id="start")
    
    data_quality_task = GreatExpectationsOperator(
        task_id="data_quality",
        data_context_root_dir="./dags/gx",
        
        data_asset_name="train_alitran",
        dataframe_to_validate=pd.read_parquet(
            f"s3://{Variable.get('bucket_name')}/work_zone/data_science_project/datasets/"
            f"{vendor_name}/train.parquet"
        ),
        
        # Set the `execution_engine` parameter equal to `"PandasExecutionEngine"`
        execution_engine="PandasExecutionEngine",
        expectation_suite_name=f"de-c2w4a1-expectation-suite",
        
        # Set `return_json_dict` as `True` to return a json-serializable dictionary
        return_json_dict=True,
        
        # Set `fail_task_on_validation_failure` as `True` 
        # to fail the Airflow task if the Great Expectation validation fails
        fail_task_on_validation_failure=True,
    )


    @task
    def train_and_evaluate(bucket_name: str, vendor_name: str):
        
        """This task trains and evaluates a regression model for a vendor."""
        
        datasets_path = (
            f"s3://{bucket_name}/work_zone/data_science_project/datasets"
        )
        
        # Use `pd.read_parquet()` to read the files created in S3 in the previous step.
        # Use the `datasets_path` and `vendor_name` to follow the format:
        # f"s3://<BUCKET_NAME>/work_zone/data_science_project/datasets/<VENDOR_NAME>/<SPLIT>.parquet",
        train = pd.read_parquet(f"{datasets_path}/{vendor_name}/train.parquet")
        test = pd.read_parquet(f"{datasets_path}/{vendor_name}/test.parquet")

        # create inputs and outputs for train and test
        X_train = train[["distance"]].to_numpy()[:, 0]
        X_test = test[["distance"]].to_numpy()[:, 0]

        y_train = train[["trip_duration"]].to_numpy()[:, 0]
        y_test = test[["trip_duration"]].to_numpy()[:, 0]

        # train the model
        model = linregress(X_train, y_train)

        # evaluate the model
        y_pred_test = model.slope * X_test + model.intercept
        performance = np.sqrt(np.average((y_pred_test - y_test) ** 2))
        print("--- performance RMSE ---")
        print(f"test: {performance:.2f}")
        
        # Return the `performance` to report the error to other tasks
        return performance


    def _is_deployable(ti):
        
        """Callable to be used by branch operator to determine whether to deploy a model"""
        
        # Use `xcom_pull` method passing the `train_and_evaluate` to get 
        # the performance value
        performance = ti.xcom_pull(task_ids="train_and_evaluate")

        # Check if the `performance` value is smaller than 500 to deploy the model
        # or notify that it's not deployable otherwise
        if performance < 500:
            print(f"is deployable: {performance}")
            return "deploy"
        else:
            print("is not deployable")
            return "notify"

    is_deployable_task = BranchPythonOperator(
        task_id="is_deployable",
        python_callable=_is_deployable, # Pass `_is_deployable` function defined above
        do_xcom_push=False,
    ) 

    @task
    def deploy():
        print("Deploying...")

    @task
    def notify(message):
        print(f"{message}. " "Notify to mail: admin@alitran.com")

    end_task = DummyOperator(task_id="end", trigger_rule="none_failed_or_skipped")
    
    (
        start_task
        >> data_quality_task
        >> train_and_evaluate(
            bucket_name="{{ var.value.bucket_name }}",
            vendor_name="alitran",
        )
        >> is_deployable_task
        >> [deploy(), notify("Not deployed")]
        >> end_task
    )

    
dag_model_trip_duration_alitran = model_trip_duration_alitran()