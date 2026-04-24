import pandas as pd
from sklearn.ensemble import IsolationForest,RandomForestClassifier
from sklearn.metrics import confusion_matrix,classification_report
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("ModelTesting/creditcard.csv")

df = pd.concat([df[df['Class'] == 0].head(50000), df[df['Class'] == 1]])

#Split features and the column that contains the result
X = df.drop(columns=['id', 'Time', 'Class'], errors='ignore')
y_true = df['Class']

#Instantianting the models
isolationForest = IsolationForest(contamination=0.02,random_state=42)
iPredictions = isolationForest.fit_predict(X)

y_pretiction = [1 if x == -1 else 0 for x in iPredictions]

print("\nRelatório de estatísticas")
print(classification_report(y_true,y_pretiction,target_names=['Normal','Fraud']))

#===================
#Confusion matrix
#===================

#Creating the figure 8x6 pol
plt.figure(figsize=(8,6))

#Calculates the math of the graph, counting the errors and scores the model made
cm = confusion_matrix(y_true,y_pretiction)

#printing the graph
sns.heatmap(cm,
            annot=True, # Paint the values on the squares
            fmt='d', # Prints the values as Int
            cmap='Blues', #Define the colour pallete
            xticklabels=['Prediction Normal','Prediction Fraud'],
            yticklabels=['Real Normal','Real Fraud'])

plt.title('Confusion matrix - Isolation Forest')
plt.ylabel('Real')
plt.xlabel('Prediction')
plt.show()

#===================
#Score distribution
#===================

df['Score_Anomaly'] = isolationForest.decision_function(X)

plt.figure(figsize=(10,6))

sns.histplot(data=df,
             x='Score_Anomaly',# X will be the AI Score
             hue='Class', #Paints the graph in different colours depending on which is fraud our normal value
             bins=50, #Breaks the x axis into 50 vertical bars
             kde=True, # draws the line over the bars
             palette={0:'blue',1:'red'})# normal is blue, fraud is red

plt.title('Anomaly Distribution')
plt.show()
