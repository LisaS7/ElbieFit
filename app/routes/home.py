from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home():
    return """
<html>
      <head><title>ElbieFit</title></head>
      <body>
        <h1>Welcome to ElbieFit</h1>
        <p>Login successful! You’ve reached the home page. Well done.</p>
      </body>
    </html>
"""
