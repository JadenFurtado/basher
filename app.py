import json
from flask import Flask, jsonify, request
from celery import Celery
import subprocess
import redis
import mysql.connector

class Database:
    def __init__(self):
        self.datbase_host = "172.19.0.2"
        self.database_name = "automation"
        self.username = "root"
        self.password = "rootpassword"
        self.mysql_connection = mysql.connector.connect(host=self.datbase_host,user=self.username,password=self.password,database=self.database_name)

    def get_scan_configurations(self):
        mycursor = self.mysql_connection.cursor(dictionary=True)
        mycursor.execute("SELECT * FROM nuclei_configuration")
        configurations = mycursor.fetchall()
        return configurations


# Initialize Flask App
app = Flask(__name__)

# Celery Configuration
app.config['CELERY_BROKER_URL'] = 'redis://172.17.0.2:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://172.17.0.2:6379/0'
app.config['REDIS_HOST'] = "172.17.0.2"
app.config['REDIS_PORT'] = 6379
app.config['REDIS_DB_NUMBER'] = 1
# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

redis_client = redis.StrictRedis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=app.config['REDIS_DB_NUMBER'], decode_responses=True)

@celery.task
def long_running_task(application_url:str,nuclei_template_url:str, nulcei_template_clone_directory:str="/tmp", output_directory:str="/tmp/",defect_dojo_url:str=None,defect_dojo_api_key:str=None):
    """
    Conduct a scan for a given application url and the corresponding nuclei templates
    """
    subprocess.run(["git", "clone",nuclei_template_url,nulcei_template_clone_directory])
    subprocess.run(["nuclei","-u",application_url,"-t",nulcei_template_clone_directory,"-je",output_directory])
    return f"Scan completed for {application_url}!"

@app.route('/check_task/<task_id>', methods=['GET'])
def check_task(task_id):
    """
    Route to check task status and result.
    """
    result = celery.AsyncResult(task_id)
    response = {"task_id": task_id, "status": result.state, "result": result.result}
    return jsonify(response)

@app.get("/scan/configurations/all")
def get_all_scan_configs():
    db = Database()
    scan_configurations = db.get_scan_configurations()
    return scan_configurations

@app.get("/scan/start/full")
def start_full_scan():
    
    db = Database()
    scan_configurations = db.get_scan_configurations()
    application_url = request.args.get("application_url","")
    nuclei_template_url = request.args.get("nuclei_template_url","")
    nuclei_template_clone_directory  = request.args.get("nuclei_template_clone_directory","")
    output_directory = request.args.get("output_directory","")
    defect_dojo_url = request.args.get("defect_dojo_url","")
    defect_dojo_api_key = request.args.get("defect_dojo_api_key")

    for config in scan_configurations:
        try:
            task = long_running_task.apply_async(args=[application_url,nuclei_template_url, nuclei_template_clone_directory, output_directory,defect_dojo_url,defect_dojo_api_key])
        except:
            print("An error occurred")
    return jsonify({"message": "Full Scan Started", "task_id": task.id}), 202

@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    """
    Returns the status of all tasks along with task ID and input parameters.
    """
    task_data = []
    for task_id, metadata in redis_client.hgetall("tasks").items():
        task_info = json.loads(metadata)
        task_result = celery.AsyncResult(task_id)

        task_data.append({
            "task_id": task_id,
            "status": task_result.state,
            "result": task_result.result if task_result.ready() else None,
            "parameters": {
                "user_id": task_info["user_id"],
                "operation": task_info["operation"],
                "value": task_info["value"]
            }
        })

    return jsonify({"tasks": task_data})

if __name__ == "__main__":
    app.run(debug=True)
