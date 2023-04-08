import psp.serializers.text as text
import json

loady = text.TextLoader()
attrs, panels = loady.loads("""DATE 2021-08-15
""")

print(attrs)
print(json.dumps(list(panels), indent=2))
