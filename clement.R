# clement file


data <- read.csv(file = "data/vessel-total-clean.csv", header = TRUE)

print(dim(data))
data[data == "\\N"] <- NA # Replace "\\N" with NA

# Check missing values
print(sum(is.na(data)))
data <- na.omit(data)


# Check for duplicates
print(sum(duplicated(data)))
data <- unique(data)
print(dim(data))

# Convert numeric columns to numeric type
num_cols <- sapply(data, is.numeric)

# Remove outliers using IQR method
for (col in names(data)[num_cols]) {
  Q1 <- quantile(data[[col]], 0.25)
  Q3 <- quantile(data[[col]], 0.75)
  IQR <- Q3 - Q1
  lower <- Q1 - (1.5 * IQR )
  upper <- Q3 + (1.5 * IQR)
  data[[col]][data[[col]] < lower | data[[col]] > upper] <- NA
}
data <- na.omit(data)


# Visualize the data
print(dim(data))
print(summary(data))