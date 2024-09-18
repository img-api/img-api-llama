import ollama
import json

article = "Intel Corp.’s (INTC) shares jumped 6.4% following report that the company qualified for $3.5 billion in federal grants to make semiconductors for the U.S. Department of Defense. Shares of The Boeing Co. (BA) fell 0.8% after the company announced plans freezing hiring and weighing temporary furloughs in the coming weeks. Shares of Nuvalent Inc.’s (NUVL) soared 28.3% after the company released positive data on two experimental cancer treatments over the weekend. Alcoa Corporation (AA) shares climbed 6.1% after the company agreed to sell its full 25.1% ownership in the Ma’aden joint venture for about $1.1 billion. Want the latest recommendations from Zacks Investment Research? Today, you can download 7 Best Stocks for the Next 30 Days. Click to get this free report The Boeing Company (BA) : Free Stock Analysis Report Intel Corporation (INTC) : Free Stock Analysis Report Alcoa (AA) : Free Stock Analysis Report Nuvalent, Inc. (NUVL) : Free Stock Analysis Report To read this article on Zacks.com click here. Zacks Investment Research"

prompt = f"from the following article evaluate the sentiment in the stock market for the company involved. \nArticle: {article} "

def run_prompt(prompt) :
    response = ollama.chat(
        model="llama3.1",
        messages=[{"role": "user", "content": prompt}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "set_article_information",
                    "description": "Set all the information about the article provided",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "a one line title describing the article",
                            },
                            "paragraph": {
                                "type": "string",
                                "description": "a one paragraph",
                            },
                            "summary": {
                                "type": "string",
                                "description": "a two to three paragraph summary",
                            },
                            "sentiment": {
                                "type": "string",
                                "enum": [ "positive", "negative", "neutral" ],
                                "description": "The sentiment positive, negative, neutral",
                            },
                            "sentiment_score": {
                                "type": "integer",
                                "description": "A value from -10 to 10 that represents how much impact will have on the stock. -10 means will go down, 10 bullish",
                            },
                        },
                        "required": ["paragraph", "sentiment", "tile", "summary"],
                    },
                },
            }
        ],
    )

    if "tool_calls" not in response["message"]:
        print("Failed loading json")
        return None

    result = response["message"]["tool_calls"]
    print(result)

    try:
        with open("test_return.json", "w") as f:
            json.dump(result, f, indent=4)

    except json.JSONDecodeError as e:
        print(f"Invalid JSON format Error: {e}")

    return True

run_prompt(prompt)