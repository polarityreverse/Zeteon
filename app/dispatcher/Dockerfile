FROM public.ecr.aws/lambda/python:3.11

ENV PYTHONUNBUFFERED=1

# Copy requirements from the local directory
COPY requirements.txt .

# Upgrade pip FIRST to avoid long resolution backtracking, then install dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the specific Lambda scripts
COPY config_lambda.py lambda_manual.py lambda_scheduled.py lambda_validator.py lambda_webhook.py ./

# Copy the utils folder into the image
COPY utils/ ./utils/

# Copy the Auth files
COPY credentials.json client_secret.json token.pickle ./

CMD ["lambda_scheduled.handler"]