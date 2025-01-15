from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)  # Waktu tunggu antara permintaan

    @task(1)
    def index(self):
        self.client.get("/")  # Mengakses halaman utama

    @task(2)
    def login(self):
        self.client.get("/login")
        self.client.post("/login", data={"username": "testuser", "password": "testpassword"})

    @task(3)
    def register(self):
        self.client.get("/register")
        self.client.post("/register", data={
            "username": "newuser",
            "password": "newpassword",
            "email": "newuser@example.com"
        })
