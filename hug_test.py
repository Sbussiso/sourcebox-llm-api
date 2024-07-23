from transformers import pipeline

def sentiment_analysis(text: str) -> str:
    model_name = "distilbert-base-uncased-finetuned-sst-2-english"
    classifier = pipeline("sentiment-analysis", model=model_name)
    result = classifier(text)
    return result[0]
