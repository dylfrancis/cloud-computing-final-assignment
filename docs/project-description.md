# Final Project — Retail Analytics on Azure Cloud

## Overview

This final group project is designed to apply cloud computing, data engineering, and data science skills using Azure Cloud Technologies and Tools. Students will analyze real-world retail data to derive insights on customer engagement and spending behaviors, delivering scalable, impactful solutions through Azure services. With the rapid growth in data across industries — especially in healthcare, finance, and retail — data analytics has become critical for advancements like drug discovery, investment analysis, and demand forecasting.

While Azure is encouraged for this project, students are also welcome to use other cloud platforms such as AWS and GCP. Additionally, real-world datasets from other industries or domains may be incorporated to align with students' professional interests, creating a more personalized learning experience.

## Project Abstract

With the rising demand for cloud and data professionals, this project provides students with hands-on experience in building end-to-end solutions on Azure Cloud. The project focuses on data ingestion, transformation, analysis, and machine learning to generate actionable insights from retail data. Using Azure's suite of data and machine learning services, students will analyze customer engagement and spending behaviors, creating an interactive web application to visualize key findings.

In this final project, students will work with anonymized retail data from 84.51°/Kroger in Azure Cloud. The main objective is to develop solutions that enhance the retail experience by simplifying life for shoppers. Creativity and empathy for the customer experience are encouraged, with a focus on the principle: **"Make the Customer's Life Easier."**

Good data science begins with good questions.

## Examples of Questions to Address

### Customer Engagement Over Time
- How does customer engagement evolve? Are households spending more or less?
- Which product categories are increasing or decreasing in popularity?

### Impact of Demographic Factors
- How do demographics (household composition, age, income, presence of children) influence customer engagement?
- How can these insights help re-engage customers within certain categories or in-store?

### Customer Segmentation
- How can we group households by demographics and spending habits for more targeted marketing?

### Loyalty Program Impact
- How does loyalty program membership affect spending and purchase frequency?

### Basket Analysis
- What are the commonly purchased product combinations, and how can they drive cross-selling opportunities?

### Seasonal and Temporal Trends
- What are the seasonal and time-based spending patterns, and how can they inform inventory and promotion planning?

### Brand and Product Preference
- What are customer preferences for private vs. national brands and organic items? How can these preferences personalize product offerings?

### Customer Lifetime Value (CLV)
- How can we predict long-term revenue potential to prioritize high-value customers?

### Churn Prediction
- Which customers are at risk of disengaging, and how can retention strategies address this?

### Socioeconomic Influence on Shopping
- How do income and household size affect purchasing behavior, and how can this support tailored marketing?

### Regional Preferences
- How do preferences vary by region, and how can inventory and promotions be adjusted to meet local demand?

### Demand Forecasting
- How can we forecast product demand to improve stock levels and minimize stockouts or overstocking?

## Data Sources

Please use the SAMPLE data set `8451_The_Complete_Journey_2_Sample.zip`, which contains household-level transactions over two years from a group of 400 households who shop at a retailer. It contains all of the purchases from each household.

### What is included in the data set?

**`400_household.csv`** — 400 sampled households
- Household demographics (if available for that household)
- Household loyalty

**`400_transactions.csv`** — Transaction data for each household (upload a minimum of 10K records)
- Date range: 8/17/2018 – 8/15/2020
- Spend
- Products
- Units
- Regional Information

**`400_products.csv`** — Product Information
- Product Number
- Department
- Commodity
- Private vs National Brand
- Natural/Organic Product Flag

## Submission

- Requested write-up information — e.g., `Final Project Group{num}_results.doc`
- Provide the code, write-ups, and URL to the Azure Web application.

## Requirements

**Total Points: 15**

### 1. Write-Up on ML Models (1 point)

Provide a brief write-up (no more than 200 words) on the following ML models:
- Linear Regression
- Random Forest
- Gradient Boosting

Select a predictive modeling technique to answer the question below. See *The Top 10 Machine Learning Algorithms* for model selection.

**Retail Question — Customer Lifetime Value (CLV):** How can we predict long-term revenue potential to prioritize high-value customers?

### 2. Web Server Setup (2 points)

- Launch and configure a web server in Azure (or another platform, as long as it's internet-accessible).
- Design an interactive webpage with the following fields:
    - Username
    - Password
    - Email

### 3. Datastore and Data Loading (2 points)

- Create a datastore or database in Azure (e.g., Azure SQL, PostgreSQL, MySQL, MongoDB, Azure Storage Account) and load sample Transactions, Households, and Products data from `8451_The_Complete_Journey_2_Sample-2-1.zip`.
- Use the free or least-cost option in Azure where possible.
- Create a display page for a Sample Data Pull for `HSHD_NUM #10`, linking the Households, Transactions, and Products tables.
- Sort by `Hshd_num`, `Basket_num`, `Date`, `Product_num`, `Department`, `Commodity` (similar to the sample data pull for HH #0001).

### 4. Interactive Web Page (2 points)

- Create a webpage that allows users to search for Data Pulls based on `Hshd_num`.
- Sort results by `Hshd_num`, `Basket_num`, `Date`, `Product_num`, `Department`, `Commodity`.

### 5. Data Loading Web App (2 points)

- Create a web app that allows loading of the latest Transactions, Households, and Products datasets.
- Test the output on the interactive web page from Requirement 4 to ensure it functions with updated data.

### 6. Web Page with Dashboard (2 points)

Design a webpage with a dashboard to explore retail challenges using selected factors from the provided "Examples of Questions to Address." Creativity is encouraged.

Possible retail questions:

- **Demographics and Engagement:** How do factors like household size, presence of children, location, and income affect customer engagement?
- **Engagement Over Time:** Are households spending more or less? Which product categories are changing in popularity?
- **Basket Analysis:** What product combinations drive cross-selling?
- **Seasonal Trends:** How do seasonal patterns inform inventory and promotions?
- **Brand Preferences:** What are customer preferences for private vs. national brands and organic items?

### 7. ML Model Application (2 points)

Use one of the following ML models — Linear Regression, Random Forest, or Gradient Boosting — to perform Basket Analysis.

**Retail Question:** What are the commonly purchased product combinations, and how can they drive cross-selling opportunities?

### 8. Churn Prediction (2 points)

**Retail Question:** Which customers are at risk of disengaging, and how can retention strategies address this?

This analysis can be supported using regression, correlation, graphical results, or all of the above.

---

> **Note:** The goal of the final project is to emphasize innovative problem-solving and strategic insights using Azure's technology stack, enabling students to deliver impactful solutions that benefit both retailers and customers.