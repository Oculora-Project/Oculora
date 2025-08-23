from setuptools import setup, find_packages

setup(
    name="oculora",
    version="0.1.0",
    packages=["config", "routers"],  # ここで明示的に指定
    install_requires=[
        "fastapi",
        "uvicorn",
        "httpx",
        "yt-dlp",
        "aiocache",
        "selenium",
        "webdriver-manager",
        "selenium-stealth",
        "psutil",
        "python-dotenv",
        "pytest",
        "pytest-asyncio"
    ],
    author="yunfie",
    author_email="yunfie.twitter+3@gmail.com",
    description="Oculora Python package",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Oculora-Project/Oculora",
)
