package com.example.finalcode

import android.os.Handler
import android.os.Looper
import io.flutter.plugin.common.EventChannel

/**
 * Bridge from the SMS receiver to any open Flutter screen.
 *
 * The receiver runs in the same process as the Flutter engine, so a static
 * reference is enough. When no screen is listening the event is dropped --
 * the message itself is still queued and synced by [SmsSync].
 */
object SmsEvents {
    private val main = Handler(Looper.getMainLooper())

    @Volatile
    private var sink: EventChannel.EventSink? = null

    fun attach(newSink: EventChannel.EventSink?) {
        sink = newSink
    }

    fun emit(event: Map<String, Any?>) {
        val current = sink ?: return
        main.post { current.success(event) }
    }
}
