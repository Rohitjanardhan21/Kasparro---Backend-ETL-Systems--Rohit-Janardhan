#!/bin/bash

echo "🔍 Verifying deployment..."

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Test health endpoint
echo "🏥 Testing health endpoint..."
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ Health endpoint: OK"
else
    echo "❌ Health endpoint: FAILED"
    exit 1
fi

# Test data endpoint
echo "📊 Testing data endpoint..."
if curl -f "http://localhost/data?limit=5" > /dev/null 2>&1; then
    echo "✅ Data endpoint: OK"
else
    echo "❌ Data endpoint: FAILED"
    exit 1
fi

# Test stats endpoint
echo "📈 Testing stats endpoint..."
if curl -f http://localhost/stats > /dev/null 2>&1; then
    echo "✅ Stats endpoint: OK"
else
    echo "❌ Stats endpoint: FAILED"
    exit 1
fi

echo ""
echo "🎉 Deployment verification completed successfully!"
echo ""
echo "📋 Available endpoints:"
echo "   • Health: http://localhost/health"
echo "   • Data:   http://localhost/data"
echo "   • Stats:  http://localhost/stats"
echo "   • Docs:   http://localhost/docs"
echo ""