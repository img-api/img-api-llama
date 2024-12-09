import requests
import json
import random

model = "llama3.3"
template = {
    "title": "write a title for the article",
    "one_paragraph": "write a simple one paragraph",
    "summary": "write a full summary here using markdown language",
    "impact": {
        "profit_loss": "neutral",
        "balance_sheet": "neutral",
        "customer_base": "neutral",
        "stock_price": "neutral",
    },
    "sentiment": "",
}

article = "Intel Corp.’s (INTC) shares jumped 6.4% following report that the company qualified for $3.5 billion in federal grants to make semiconductors for the U.S. Department of Defense. Shares of The Boeing Co. (BA) fell 0.8% after the company announced plans freezing hiring and weighing temporary furloughs in the coming weeks. Shares of Nuvalent Inc.’s (NUVL) soared 28.3% after the company released positive data on two experimental cancer treatments over the weekend. Alcoa Corporation (AA) shares climbed 6.1% after the company agreed to sell its full 25.1% ownership in the Ma’aden joint venture for about $1.1 billion. Want the latest recommendations from Zacks Investment Research? Today, you can download 7 Best Stocks for the Next 30 Days. Click to get this free report The Boeing Company (BA) : Free Stock Analysis Report Intel Corporation (INTC) : Free Stock Analysis Report Alcoa (AA) : Free Stock Analysis Report Nuvalent, Inc. (NUVL) : Free Stock Analysis Report To read this article on Zacks.com click here. Zacks Investment Research"

prompt = f"from the following article evaluate the impact on the following categories in the JSON template. The values for the impact are long term positive, negative, neutral \nArticle: [ {article} ] Use the following template: {json.dumps(template)}."

data = {
    "prompt": prompt,
    "model": model,
    "format": "json",
    "stream": False,
    "options": {"temperature": 0.5, "top_p": 0.99, "top_k": 100},
}

print(f"Generating a sample user")
response = requests.post("http://localhost:11434/api/generate", json=data, stream=False)
json_data = json.loads(response.text)
print(json.dumps(json.loads(json_data["response"]), indent=2))
