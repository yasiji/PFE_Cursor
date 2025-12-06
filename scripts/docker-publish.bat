@echo off
REM Script to build and publish Docker images to Docker Hub
REM Usage: docker-publish.bat <dockerhub-username> [version]

setlocal

set DOCKERHUB_USER=%1
set VERSION=%2

if "%DOCKERHUB_USER%"=="" (
    echo Usage: docker-publish.bat ^<dockerhub-username^> [version]
    echo Example: docker-publish.bat myusername v1.0
    exit /b 1
)

if "%VERSION%"=="" set VERSION=latest

set APP_NAME=pfe-replenishment

echo.
echo ============================================
echo   Docker Hub Publisher
echo ============================================
echo   User: %DOCKERHUB_USER%
echo   Version: %VERSION%
echo ============================================
echo.

REM Login to Docker Hub
echo Logging in to Docker Hub...
docker login

REM Build backend image
echo.
echo [1/4] Building backend image...
docker build -t %DOCKERHUB_USER%/%APP_NAME%-backend:%VERSION% .

REM Build frontend image
echo.
echo [2/4] Building frontend image...
docker build -t %DOCKERHUB_USER%/%APP_NAME%-frontend:%VERSION% -f Dockerfile.frontend .

REM Push backend
echo.
echo [3/4] Pushing backend to Docker Hub...
docker push %DOCKERHUB_USER%/%APP_NAME%-backend:%VERSION%

REM Push frontend
echo.
echo [4/4] Pushing frontend to Docker Hub...
docker push %DOCKERHUB_USER%/%APP_NAME%-frontend:%VERSION%

echo.
echo ============================================
echo   SUCCESS! Images published to Docker Hub
echo ============================================
echo.
echo Anyone can now run your app with:
echo.
echo   docker pull %DOCKERHUB_USER%/%APP_NAME%-backend:%VERSION%
echo   docker pull %DOCKERHUB_USER%/%APP_NAME%-frontend:%VERSION%
echo.
echo Or use the docker-compose file!
echo.

endlocal

