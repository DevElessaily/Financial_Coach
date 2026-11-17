# finalcode

Flutter app + FastAPI backend for tracking expenses, with SMS history read
straight from the Android inbox.

## Backend

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Interactive docs: <http://127.0.0.1:8000/docs>
- The SQLite database lives at `Backend/app.db` and is created on first start,
  no matter which directory uvicorn is launched from.
- Override the database with `DATABASE_URL` (e.g. in `Backend/.env`).

### Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/transactions?limit=50` | Recent transactions |
| `POST` | `/api/transactions` | Create one (`amount`, `category`, `type`: `income` / `expense` / `transfer`) |
| `DELETE` | `/api/transactions/{id}` | Delete a transaction |
| `GET`, `POST`, `DELETE` | `/api/categories` | List, create, and delete unused categories |
| `POST` | `/api/sms/filter` | Store a single SMS (`sender`, `message`, `date` = epoch seconds) |
| `POST` | `/api/sms/bulk` | Store many at once (`{"items": [...]}`), duplicates skipped |
| `GET` | `/api/sms/history?limit=100` | Synced SMS, newest first |
| `POST` | `/api/sms/parse` | Preview SMS transaction extraction |
| `POST` | `/api/sms/process` | Retry processing stored SMS |
| `POST` | `/api/sms/process-stored` | Reprocess stored SMS in batches |
| `GET`, `POST`, `DELETE` | `/api/alerts` | Manage transaction threshold alerts |
| `GET`, `POST` | `/api/notifications` | Read and create in-app notifications |
| `GET` | `/api/users/me` | Get the local user and account |
| `GET`, `PUT`, `DELETE` | `/api/currency-maps` | Manage currency names and aliases |
| `GET`, `PUT`, `DELETE` | `/api/currency` | Manage supported currencies |
| `POST` | `/api/currency/convert` | Convert currencies using the exchange-rate provider |
| `GET`, `POST`, `DELETE` | `/api/sms-senders` | Manage SMS sender identities |
| `GET`, `POST`, `PATCH`, `DELETE` | `/api/sms-regex` | Manage sender-specific SMS parsing patterns |
| `GET`, `POST` | `/api/pending-transactions` | Create and review pending transactions |
| `GET` | `/api/pending-category-reviews` | Category review queue |

## Flutter app

```powershell
flutter pub get
flutter run
```

Then in the app:

1. **Settings** → set the backend URL to your PC's LAN IP, e.g.
   `http://192.168.1.10:8000` (the emulator default is `http://10.0.2.2:8000`),
   tap **Test**, then **Save**. The URL is remembered between launches.
2. **SMS Tracking History** → allow SMS access when Android asks. The
   *On this phone* tab lists the device inbox; **Sync to server** pushes it to
   the backend, and the *Synced* tab shows what the server stored. Recognized
   completed payments and deposits are added as transactions.
3. **Live sync** — with SMS permission granted, a `SMS_RECEIVED` receiver
   captures every new message and posts it to `/api/sms/bulk` immediately,
   even when the app is closed. Messages that cannot be delivered (backend
   offline, wrong URL) are queued on the phone and retried on the next launch
   or the next incoming SMS; the history page shows the queue size.
4. **Add Transaction** → enter amount, pick a category, choose
   income/expense/transfer; new entries appear in Recent Activity.
5. **Insights** summarizes recorded transactions. **Wize** answers basic
   spending and income questions from that history. The center microphone uses
   Android speech recognition to prefill a draft; review it before saving.

The phone and the PC must be on the same Wi-Fi network. If the app cannot
reach the server, check Windows Firewall allows inbound TCP 8000.

### Build an APK

```powershell
flutter build apk --debug
# build\app\outputs\flutter-apk\app-debug.apk
```

## Alternative: sync from Termux (Python)

The Kotlin receiver only exists inside the APK. If you prefer Python, these
scripts do the same job on the phone through Termux:

| File | Purpose |
| --- | --- |
| `scripts/sms_sync.py` | HTTP upload + offline queue (Python port of `SmsSync.kt`) |
| `scripts/sms_receiver.py` | Watches the inbox and uploads new SMS (Python port of `SmsReceiver.kt`) |
| `sms_history_sync.py` | One-off history upload for the last 1/3/6 months |

```bash
pkg install python termux-api
termux-wake-lock

# watch for new SMS (poll every 20 s by default)
python scripts/sms_receiver.py --base-url http://192.168.1.10:8000

# single poll, e.g. from cron or Tasker
python scripts/sms_receiver.py --base-url http://192.168.1.10:8000 --once

# push the existing inbox once
python scripts/sms_receiver.py --base-url http://192.168.1.10:8000 --once --backfill
```

`scripts/sms_sync.py` also works on its own:

```bash
python scripts/sms_sync.py --base-url http://192.168.1.10:8000 --status
python scripts/sms_sync.py --base-url http://192.168.1.10:8000 --flush
python scripts/sms_sync.py --base-url http://192.168.1.10:8000 --add "Bank" "You paid 50 EGP"
```

Batch history upload:

```bash
python sms_history_sync.py \
  --months 3 \
  --endpoint http://192.168.1.10:8000/api/sms/filter \
  --dry-run          # preview first, then drop --dry-run to send
```

Use `--sender "Bank"` (repeatable) to limit which senders are uploaded.

> Android only delivers `SMS_RECEIVED` to native code, so the Python watcher
> polls the inbox instead of reacting to a broadcast: a message reaches the
> backend within one `--interval` (default 20 s), and only while the script
> runs. The Kotlin receiver in the APK is instant and works with the app closed.

## File map (SMS)

| Layer | File |
| --- | --- |
| Android permissions / receiver | `android/app/src/main/AndroidManifest.xml` |
| Inbox read + permissions + event channel | `android/app/src/main/kotlin/com/example/finalcode/MainActivity.kt` |
| Real-time `SMS_RECEIVED` receiver | `android/app/src/main/kotlin/com/example/finalcode/SmsReceiver.kt` |
| HTTP upload + offline queue (Kotlin) | `android/app/src/main/kotlin/com/example/finalcode/SmsSync.kt` |
| Receiver → Flutter bridge | `android/app/src/main/kotlin/com/example/finalcode/SmsEvents.kt` |
| Flutter UI, live events, history | `lib/main.dart` |
| Python upload + offline queue | `scripts/sms_sync.py` |
| Python inbox watcher | `scripts/sms_receiver.py` |
| Python history upload | `sms_history_sync.py` |
| Server endpoints | `Backend/app/api/routes/sms_filter.py` |
| Database model | `Backend/app/models/sms.py` |

## Checks

```powershell
cd Backend; .\.venv\Scripts\python -m compileall -q app
flutter analyze
flutter test
```
