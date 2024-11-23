find DATA/JSON_TO_PROCESS -type f -name "*.json" -exec sed -i 's|https://tothemoon.life/api/news/ai_callback|http://dev.tothemoon.life/api/news/ai_callback|g' {} +
find DATA/FAILED -type f -name "*.json" -exec sed -i 's|https://tothemoon.life/api/news/ai_callback|http://dev.tothemoon.life/api/news/ai_callback|g' {} +


find DATA/JSON_TO_PROCESS -type f -name "*.json" -exec sed -i 's|https://tothemoon.life/api/article/ai_callback|http://dev.tothemoon.life/api/news/ai_callback|g' {} +
find DATA/FAILED -type f -name "*.json" -exec sed -i 's|https://tothemoon.life/api/article/ai_callback|http://dev.tothemoon.life/api/news/ai_callback|g' {} +



