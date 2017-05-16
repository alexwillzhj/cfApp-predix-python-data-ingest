# python app for machine learning

A python-based Cloud Foundry application implementing typical classifier training and testing.


## Pre-requisites
To run this analytic locally, you will need to have the following:
- Python 2.7+
- Flask 0.10+

# Data source
This app is combined with data microservice from GE Predix platform, i.e., Timeseries, and Redis, which can be found from Cloud Foundry marketplace.

Timeseries is used to store feature and label, i.e., "ts_detection_feature0001" and "ts_detection_label0001". Multiples samples are stored under different time tag. In this case, this app has data ingested for every 10 seconds. The training session will use past X samples, and the testing session will test the most recent Y sample. X and Y are adjustable.

The trained model is stored in Redis database as <model_name, model_body> pair. The model per se is generated in Python, e.g., LinearRegression or RandomForestClassifier, and use cPickle to serielize the model structure to string. The format of both model_name and model_body are String.


