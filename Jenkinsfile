pipeline {
    agent any

    environment {
        REPO_URL = "https://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@github.com/Bhargav-Datafactz/DataFactZ_HRMS.git"
        BRANCH = "bhargav"
        DOCKER_IMAGE = "your-dockerhub-username/django-app"
        DOCKER_HUB_CREDENTIALS = "docker-hub-credentials"
        CONTAINER_NAME = "django-app"
        PORT_MAPPING = "8000:8000"
    }

    stages {
        stage('Clone Repository') {
            steps {
                git branch: "$BRANCH", url: "$REPO_URL"
                sh "ls -la"  // Check if files are present
            }
        }
        stage('Verify Repository Content') {
            steps {
                sh "ls -la"
            }
        }


        stage('Generate Docker Image Tag') {
            steps {
                script {
                    env.GIT_COMMIT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
                    env.IMAGE_TAG = "${env.DOCKER_IMAGE}:${env.GIT_COMMIT}"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t $IMAGE_TAG ."
            }
        }

        stage('Run Django Migrations') {
            steps {
                sh "docker run --rm $IMAGE_TAG python manage.py migrate"
            }
        }

        stage('Push Docker Image to Docker Hub') {
            steps {
                withDockerRegistry([credentialsId: "$DOCKER_HUB_CREDENTIALS", url: '']) {
                    sh "docker push $IMAGE_TAG"
                    sh "docker tag $IMAGE_TAG $DOCKER_IMAGE:latest"
                    sh "docker push $DOCKER_IMAGE:latest"
                }
            }
        }

        stage('Deploy in VM') {
            steps {
                sh """
                # Stop and remove existing container
                docker stop $CONTAINER_NAME || true
                docker rm $CONTAINER_NAME || true

                # Pull the latest image
                docker pull $IMAGE_TAG

                # Run the Django app using Gunicorn
                docker run -d --name $CONTAINER_NAME -p $PORT_MAPPING $IMAGE_TAG gunicorn --bind 0.0.0.0:8000 your_project.wsgi:application

                # Remove unused images to save space
                docker image prune -f
                """
            }
        }
    }

    post {
        success {
            echo "✅ Deployment successful!"
        }
        failure {
            echo "❌ Deployment failed!"
        }
    }
}
