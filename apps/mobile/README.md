# Flutter client

Install Flutter, then:

```bash
flutter pub get
flutter run -d chrome --dart-define=API_URL=http://localhost:8000
```

For Android emulator use:
```bash
flutter run --dart-define=API_URL=http://10.0.2.2:8000
```

The repository also contains a browser PWA at the FastAPI root URL, which is the easiest first demo.
