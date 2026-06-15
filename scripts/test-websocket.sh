#!/bin/bash
# Test WebSocket connection properly

echo "Testing WebSocket endpoint..."
echo ""

# Test 1: Check if endpoint exists (GET should return 404 with JSON)
echo "1. GET /dashboard/ws/events (should be 404):"
curl -s "https://litimez.ai/dashboard/ws/events" -w "\nStatus: %{http_code}\n\n"

# Test 2: Check if API health works
echo "2. GET /dashboard/api/health:"
curl -s "https://litimez.ai/dashboard/api/health"
echo ""

# Test 3: Test WebSocket handshake (OPTIONS)
echo "3. OPTIONS /dashboard/ws/events (preflight):"
curl -s -X OPTIONS "https://litimez.ai/dashboard/ws/events" -H "Origin: https://litimez.ai" -w "\nStatus: %{http_code}\n\n"

# Test 4: Direct WebSocket connection attempt
echo "4. Testing raw WebSocket handshake (will fail without proper upgrade):"
curl -s -N -H "Connection: Upgrade" -H "Upgrade: websocket" "https://litimez.ai/dashboard/ws/events" 2>&1 | head -5

echo ""
echo "Done!"
