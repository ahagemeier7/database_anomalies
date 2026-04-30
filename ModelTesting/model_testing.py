import pandas as pd
from sklearn.ensemble import IsolationForest,RandomForestClassifier
from sklearn.metrics import confusion_matrix,classification_report
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import seaborn as sns

#Implemented from scratch
from Models.RandomForest import RandomForest

df = pd.read_csv("ModelTesting/creditcard.csv")

df = pd.concat([df[df['Class'] == 0].head(50000), df[df['Class'] == 1]])

#Split features and the column that contains the result
X = df.drop(columns=['id', 'Time', 'Class'], errors='ignore')
y_true = df['Class']

#Instantianting the models
isolationForest = IsolationForest(contamination=0.02,random_state=42)
iPredictions = isolationForest.fit_predict(X)

y_prediction = [1 if x == -1 else 0 for x in iPredictions]

print("\nStatistics report")
print(classification_report(y_true,y_prediction,target_names=['Normal','Fraud']))

#===================
#Confusion matrix
#===================

#Creating the figure 8x6 pol
plt.figure(figsize=(8,6))

#Calculates the math of the graph, counting the errors and scores the model made
cm = confusion_matrix(y_true,y_prediction)

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

#------------------------------------------------

#Random forest classifier
#Defining dataframes
X_rfc = df.drop(columns=['id', 'Time', 'Class', 'Score_Anomaly'], errors='ignore')
y_true_rfc = df['Class']

#Splitting the data into training data and test data
X_train, X_test, y_train, y_test = train_test_split(
  X_rfc, #the data matrix
  y_true_rfc, # the anwsers
  test_size=0.3, # 30% of the data will be used as test and 70 for training
  random_state=42, #Ensuring that the script will always separate the same 70/30 rows
  stratify=y_true_rfc) #Stratify makes the frauds to be "split" between both data sets


model_rf = RandomForestClassifier(n_estimators=100#Number of decision tree
                                  ,random_state=42,
                                  n_jobs=-1)#Using all cpus avaliable to train the model

#The learning function
model_rf.fit(X_train,y_train)

#Predicting
y_prediction = model_rf.predict(X_test)

#This gets how sure the model was on his predictions. The [:,1] oly gets the probabilyty on the set,
# and ignores the rest of the columns
y_probability = model_rf.predict_proba(X_test)[:,1]

print(classification_report(y_test,y_pred=y_prediction,target_names=['Normal','Fraud']))

#===================
#Confusion matrix
#===================
plt.figure(figsize=(8,6))
cm = confusion_matrix(y_test, y_prediction)

sns.heatmap(cm, annot=True, fmt='d', cmap='Greens', 
            xticklabels=['Prediction Normal','Prediction Fraud'],
            yticklabels=['Real Normal','Real Fraud'])

plt.title('Confusion matrix - Random Forest (Supervisionado)')
plt.ylabel('Real')
plt.xlabel('Prediction')
plt.show()


#===================
#Probability distribution
#===================

df_graph = pd.DataFrame({
  'Fraud_probability': y_probability,
  'Class': y_test.values
})

plt.figure(figsize=(10,6))
sns.histplot(data=df_graph,
             x='Fraud_probability',
             hue='Class', 
             bins=50, 
             kde=True, 
             palette={0:'blue', 1:'red'})


plt.title('Probability of a fraud (0.0 = 0% | 1.0 = 100%)')
plt.xlabel('Fraud chance (Above .5 the model blocks)')
plt.show()




#-------------------------------------------------------------

# df = pd.concat([df[df['Class'] == 0].head(5000), df[df['Class'] == 1]])

# X = df.drop(columns=['id', 'Time', 'Class'], errors='ignore')
# y_true = df['Class']


# X_train, X_test, y_train, y_test = train_test_split(X, y_true, test_size=0.3, random_state=42, stratify=y_true)

# X_train_np = X_train.values
# y_train_np = y_train.values
# X_test_np = X_test.values
# y_test_np = y_test.values


# rf_scratch = RandomForest(n_trees=3, max_depth=5, min_samples_split=2)

# rf_scratch.fit(X_train_np, y_train_np)

# y_prediction = rf_scratch.predict(X_test_np)


# print(classification_report(y_test_np, y_prediction, target_names=['Normal','Fraud']))

# # ==============================================================
# # Confusion matrix
# # ==============================================================
# plt.figure(figsize=(8,6))
# cm = confusion_matrix(y_test_np, y_prediction)

# sns.heatmap(cm, annot=True, fmt='d', cmap='Purples',
#             xticklabels=['Prediction Normal','Prediction Fraud'],
#             yticklabels=['Real Normal','Real Fraud'])

# plt.title('Confusion matrix - Random forest (From Scratch)')
# plt.ylabel('Real')
# plt.xlabel('prediction')
# plt.show()


#----------------------------------------------------
#Classification report - Isolation Forest
#----------------------------------------------------
#                 precision    recall  f1-score   support

#       Normal       1.00      0.99      0.99     50000
#        Fraud       0.31      0.63      0.41       492

#     accuracy                           0.98     50492
#    macro avg       0.65      0.81      0.70     50492
# weighted avg       0.99      0.98      0.99     50492


#Understanding the classification report

#Column Support
#Ths is the reality, meaning that we had 50000 normal values and 492 anomalies

#Column Recall
#This is the question: "On 492 anomalies, how many did the model catch?"
#The answer would be: "The model caught 63% of them"

#Column Precision
# this is the odds that tells that each time that the model thougth something is an anomalie, wich one you were right (False positives)
# On Isolation forest, it was right only 37% of the time

#Column f1-score
#This is the average between recall and precision. Isolation forest only had 4.1 out of 10

#The Accuracy ilusion
# This is a indicator that's not usefull for anomaly detection.
#We can imagine a situation where a security is guarding an entrance.
#if the security just lets everybody pass 50000 where honest customers and 492 were thieves.
#So the model only got 492 wrong, getting a high accuracy, in this case 99%

#-----Conclusion-----
#Isolation forest gets a score of 4.1, so its understandable because it doesnt really know what is an anomaly,
#The model just points out on rows that aren't similar from the other, that not necessarily are anomalies
#This model then is usefull to find new anomalies, but it shouldn't be the only model "Protecting" the database.


#----------------------------------------------------
#Classification report - Random Forest Classifier
#----------------------------------------------------
#                 precision    recall  f1-score   support

#       Normal       1.00      1.00      1.00     15000
#        Fraud       0.97      0.84      0.90       148

#     accuracy                           1.00     15148
#    macro avg       0.98      0.92      0.95     15148
# weighted avg       1.00      1.00      1.00     15148

#Reading this report we can see that a supervised model, have a way higher score, 
#and this is understandable because we hand a paper for the model, containing the data on who are the thieves, and it had
#to find the other thieves based on that.
# The problem with this model is that if a completlely different anomaly appears, it wouldn't recognize it.


#The best approach for this project is to use a hybrid architecture, blending both models to protect against new anomalies, and still have a high accuracy 
#from RandomForest Classifier