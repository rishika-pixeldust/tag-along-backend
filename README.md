# tag-along-backend

Django REST API for the Tag Along app.

## Render free tier and request timeouts

On Render's **free** plan, the web service spins down after about 15 minutes of no traffic. The **first request** after a spin-down (cold start) can take **30–60+ seconds** while the instance starts. If your client uses a 30s receive timeout, that first request will fail with a timeout.

**Fix (in the Flutter/mobile client):** set a longer `receiveTimeout` for the API client (e.g. **60–90 seconds**) so the first request after a cold start can complete. For example with Dio:

```dart
BaseOptions(
  baseUrl: 'https://tag-along-backend-ftp9.onrender.com',
  connectTimeout: const Duration(seconds: 30),
  receiveTimeout: const Duration(seconds: 90), // allow cold start
)
```

Optional: you can call `GET /api/v1/health/` first with the same long timeout to "wake" the server, then call `/api/v1/auth/profile/` so subsequent requests are fast.
