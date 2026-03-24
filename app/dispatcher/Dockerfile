FROM public.ecr.aws/lambda/python:3.11

# Copy requirements from the local directory
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the specific Lambda scripts
COPY config_lambda.py lambda_manual.py lambda_scheduled.py lambda_validator.py lambda_webhook.py ./

# Copy the utils folder into the image
COPY utils/ ./utils/

# Copy the Auth files
COPY credentials.json client_secret.json token.pickle ./

CMD ["lambda_scheduled.handler"]