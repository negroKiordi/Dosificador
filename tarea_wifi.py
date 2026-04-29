#tarea_wifi — controla AP, botón y auto‑apagado

import uasyncio as asyncio
import network
import utime
import machine
import config

AP_ESSID = config.essid
AP_PASS = config.password 

async def tarea_wifi():
    boton = machine.Pin(config.PIN_BOTON_WIFI, machine.Pin.IN, machine.Pin.PULL_UP)
    led   = machine.Pin(config.LED_WIFI, machine.Pin.OUT)
    led.value(0)
    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    wifi_active = False
    button_pressed = False
    activation_time = 0
    last_client_time = 0

    def get_num_clients():
        if not ap.active():
            return 0
        try:
            stations = ap.status('stations')
            return len(stations) if isinstance(stations, (list, tuple)) else 0
        except:
            return 0

    def activate_ap():
        nonlocal wifi_active, activation_time, last_client_time
        print("\n🔌 Activando WiFi AP 'Antiempaste'...")
        try:
            ap.active(False)
        except:
            pass
        try:
            ap.config(essid=AP_ESSID, password=AP_PASS,
                      authmode=network.AUTH_WPA_WPA2_PSK)
            ap.active(True)
            ip = ap.ifconfig()[0]
            print("✅ AP activo - IP:", ip)
            led.value(1)
            wifi_active = True
            activation_time = utime.ticks_ms()
            last_client_time = 0
        except Exception as e:
            print("❌ Error activando AP:", e)

    def deactivate_ap():
        nonlocal wifi_active, activation_time, last_client_time
        print("🔋 Apagando WiFi para ahorrar batería...")
        try:
            ap.active(False)
        except:
            pass
        led.value(0)
        wifi_active = False
        activation_time = 0
        last_client_time = 0

    print("tarea_wifi iniciada")
    while True:
        # botón (PULL_UP)
        if boton.value() == 0:
            if not button_pressed:
                button_pressed = True
                if not wifi_active:
                    activate_ap()
        else:
            button_pressed = False

        if wifi_active:
            now = utime.ticks_ms()
            num_clients = get_num_clients()
            if num_clients > 0:
                last_client_time = now

            should_deactivate = False
            if num_clients == 0:
                if last_client_time == 0:
                    if utime.ticks_diff(now, activation_time) >= 60000:
                        should_deactivate = True
                else:
                    if utime.ticks_diff(now, last_client_time) >= 10000:
                        should_deactivate = True

            if should_deactivate:
                deactivate_ap()

        await asyncio.sleep_ms(200)
