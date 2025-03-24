from functools import reduce

# Convert a list of strings to uppercase
pets = ['alfred', 'tabitha', 'william', 'arla']
uppercased_pets = list(map(str.upper, pets))
print(uppercased_pets)
# Output: ['ALFRED', 'TABITHA', 'WILLIAM', 'ARLA']

# Filter out odd numbers from a list
numbers = [1, 2, 3, 4, 5, 6]
even_numbers = list(filter(lambda x: x % 2 == 0, numbers))
print(even_numbers)
# Output: [2, 4, 6]

# Calculate the product of a list of numbers
numbers = [1, 2, 3, 4, 5, 10]
product = reduce(lambda x, y: x * y, numbers)
print(product)
# Output: 120

# Combine two lists element-wise
names = ['Alice', 'Bob', 'Charlie']
scores = [85, 90, 95]
combined = list(zip(names, scores))
print(combined)
# Output: [('Alice', 85), ('Bob', 90), ('Charlie', 95)]


