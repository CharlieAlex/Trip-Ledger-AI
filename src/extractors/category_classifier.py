"""Category classifier for receipt items.

Uses LLM-based classification or simple rule-based fallbacks
to categorize items into predefined categories.
"""

from src.config import Config
from src.etl.models import Category


class CategoryClassifier:
    """Classify items into categories."""

    # Keywords for rule-based classification fallback
    CATEGORY_KEYWORDS: dict[Category, list[str]] = {
        Category.FOOD: [
            # Japanese
            "おにぎり", "弁当", "パン", "サンドイッチ", "ラーメン", "寿司", "うどん", "そば",
            "カレー", "定食", "丼", "ハンバーガー", "ピザ", "菓子", "スナック", "チョコ",
            # English
            "rice", "bread", "sandwich", "noodle", "sushi", "curry", "burger", "pizza",
            "snack", "chocolate", "candy", "meal", "food", "lunch", "dinner", "breakfast",
            # Chinese
            "飯", "麵", "便當", "餐", "小吃", "零食",
        ],
        Category.BEVERAGE: [
            # Japanese
            "お茶", "コーヒー", "ジュース", "水", "ビール", "酒", "ワイン", "ミルク",
            "ドリンク", "飲料",
            # English
            "tea", "coffee", "juice", "water", "beer", "wine", "milk", "drink", "beverage",
            "soda", "coke", "cola",
            # Chinese
            "茶", "咖啡", "果汁", "飲料", "啤酒", "酒",
        ],
        Category.TRANSPORT: [
            # Japanese
            "切符", "乗車券", "特急", "新幹線", "バス", "タクシー", "地下鉄", "電車",
            "ガソリン", "駐車", "航空", "フライト",
            # English
            "ticket", "train", "bus", "taxi", "subway", "metro", "gas", "fuel", "parking",
            "flight", "airline", "uber", "grab",
            # Chinese
            "車票", "機票", "計程車", "公車", "捷運", "高鐵", "油資", "停車",
        ],
        Category.LODGING: [
            # Japanese
            "ホテル", "旅館", "民宿", "宿泊",
            # English
            "hotel", "hostel", "airbnb", "inn", "lodge", "accommodation", "room", "stay",
            # Chinese
            "飯店", "旅館", "民宿", "住宿",
        ],
        Category.SHOPPING: [
            # Japanese
            "服", "靴", "バッグ", "アクセサリー", "お土産", "雑貨", "化粧品", "電子",
            # English
            "clothing", "clothes", "shoes", "bag", "souvenir", "gift", "cosmetic",
            "electronics", "phone", "accessory",
            # Chinese
            "衣服", "鞋", "包", "紀念品", "禮物", "化妝品", "電子",
        ],
        Category.ENTERTAINMENT: [
            # Japanese
            "入場", "チケット", "映画", "遊園地", "博物館", "美術館", "観光",
            # English
            "ticket", "admission", "movie", "cinema", "museum", "park", "attraction",
            "tour", "show", "concert", "game",
            # Chinese
            "門票", "電影", "遊樂園", "博物館", "美術館", "觀光",
        ],
        Category.HEALTH: [
            # Japanese
            "薬", "医療", "病院", "クリニック", "ドラッグ",
            # English
            "medicine", "pharmacy", "drug", "medical", "clinic", "hospital", "health",
            # Chinese
            "藥", "醫療", "診所", "醫院",
        ],
    }

    def classify(self, item_name: str, context: str | None = None) -> Category:
        """Classify an item into a category.

        Uses keyword matching as a fallback classification method.
        Primary classification is done by Gemini during extraction.

        Args:
            item_name: Name of the item
            context: Optional context (e.g., store type)

        Returns:
            Category enum value
        """
        item_lower = item_name.lower()

        # Check each category's keywords
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in item_lower:
                    return category

        # Use context if available
        if context:
            context_lower = context.lower()
            # Check if context matches any category keywords
            for category, keywords in self.CATEGORY_KEYWORDS.items():
                for keyword in keywords:
                    if keyword.lower() in context_lower:
                        return category

        return Category.OTHER

    @staticmethod
    def get_subcategory(item_name: str, category: Category) -> str | None:
        """Get subcategory for an item.

        Args:
            item_name: Name of the item
            category: Main category

        Returns:
            Subcategory string or None
        """
        item_lower = item_name.lower()

        subcategory_keywords = {
            Category.FOOD: {
                "meal": ["定食", "弁当", "ランチ", "lunch", "dinner", "breakfast", "餐"],
                "snack": ["おにぎり", "パン", "菓子", "snack", "candy", "chocolate", "零食"],
                "groceries": ["grocery", "食材", "野菜", "fruit"],
            },
            Category.BEVERAGE: {
                "coffee": ["コーヒー", "coffee", "咖啡", "カフェ", "latte", "espresso"],
                "alcohol": ["ビール", "酒", "ワイン", "beer", "wine", "sake", "啤酒"],
                "soft_drink": ["ジュース", "juice", "soda", "cola", "coke", "果汁"],
            },
            Category.TRANSPORT: {
                "train": ["電車", "新幹線", "特急", "train", "railway", "火車", "高鐵"],
                "taxi": ["タクシー", "taxi", "uber", "grab", "計程車"],
                "flight": ["航空", "flight", "airline", "機票", "飛機"],
                "fuel": ["ガソリン", "gas", "fuel", "油資"],
            },
            Category.LODGING: {
                "hotel": ["ホテル", "hotel", "飯店"],
                "hostel": ["ホステル", "hostel", "青旅"],
                "airbnb": ["airbnb", "民泊", "民宿"],
            },
            Category.SHOPPING: {
                "clothing": ["服", "clothes", "clothing", "衣服", "shirt", "pants"],
                "souvenir": ["お土産", "souvenir", "gift", "紀念品", "禮物"],
                "electronics": ["電子", "electronics", "phone", "電器"],
            },
            Category.ENTERTAINMENT: {
                "ticket": ["チケット", "ticket", "入場", "門票"],
                "activity": ["体験", "experience", "tour", "活動"],
                "attraction": ["遊園地", "park", "museum", "遊樂園", "博物館"],
            },
            Category.HEALTH: {
                "pharmacy": ["薬局", "ドラッグ", "pharmacy", "drug", "藥局"],
                "medical": ["医療", "病院", "clinic", "醫療", "診所"],
            },
        }

        if category in subcategory_keywords:
            for subcat, keywords in subcategory_keywords[category].items():
                for keyword in keywords:
                    if keyword.lower() in item_lower:
                        return subcat

        return None

    @staticmethod
    def get_category_info(category: Category) -> dict:
        """Get category metadata (emoji, label).

        Args:
            category: Category enum

        Returns:
            Dict with emoji and label
        """
        return Config.CATEGORIES.get(
            category.value,
            {"emoji": "📦", "label": "其他"}
        )


# Convenience function
def classify_item(item_name: str, context: str | None = None) -> tuple[Category, str | None]:
    """Classify an item and get its subcategory.

    Args:
        item_name: Name of the item
        context: Optional context

    Returns:
        Tuple of (category, subcategory)
    """
    classifier = CategoryClassifier()
    category = classifier.classify(item_name, context)
    subcategory = classifier.get_subcategory(item_name, category)
    return category, subcategory
