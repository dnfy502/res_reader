from unstructured.partition.auto import partition

elements = partition("Dataset_Second.pdf")

print(elements[1].text)