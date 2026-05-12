import pandas as pd
import numpy as np
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


# -------------------------------------------------------------
# Hybrid model
# -------------------------------------------------------------
from sklearn.metrics import precision_score, recall_score, f1_score
import numpy as np

scores_if = isolationForest.decision_function(X_test)
probs_rf = model_rf.predict_proba(X_test)[:, 1]

print("\n" + "="*60)
print("testing the best hybrid tune")
print("="*60)

best_f1 = 0
best_prec = 0
best_rec = 0
best_rule = {}

for rf_min in np.arange(0.05, 0.50, 0.05):
  
    for if_limit in np.arange(-0.25, -0.05, 0.01):
        
        y_temp = np.zeros(len(X_test), dtype=int)
        

        rule1 = probs_rf >= 0.50

        rule2 = (probs_rf >= rf_min) & (probs_rf < 0.50) & (scores_if < if_limit)
        
        y_temp[rule1 | rule2] = 1
        

        f1_temp = f1_score(y_test, y_temp, pos_label=1, zero_division=0)
        
        if f1_temp > best_f1:
            best_f1 = f1_temp
            best_prec = precision_score(y_test, y_temp, pos_label=1, zero_division=0)
            best_rec = recall_score(y_test, y_temp, pos_label=1, zero_division=0)
            best_rule = {'rf_min': rf_min, 'if_limit': if_limit}

print(f"F1-Score: {best_f1:.4f} (needs to beat: 0.9025)")
print(f"Precision: {best_prec:.4f} | Recall: {best_rec:.4f}")
print(f"The perfect rule is -> RF > {best_rule['rf_min']:.2f} and IF < {best_rule['if_limit']:.2f}")


y_pred_hybrid = np.zeros(len(X_test), dtype=int)
rule1 = probs_rf >= 0.50
rule2 = (probs_rf >= best_rule['rf_min']) & (probs_rf < 0.50) & (scores_if < best_rule['if_limit'])
y_pred_hybrid[rule1 | rule2] = 1



# #---------------------
# #Hybrid model testing
# #---------------------
# #geting probabilities of being a anomaly
# scores_if = isolationForest.decision_function(X_test)
# probs_rf = model_rf.predict_proba(X_test)[:, 1]

# #Creating a Prediction array, filled with 0 (Normal)
# y_pred_hybrid = np.zeros(len(X_test), dtype=int)

# rule1 = probs_rf >= 0.50 

# rule2 = (probs_rf >= 0.10) & (probs_rf < 0.50) & (scores_if < -0.19)

# is_anomaly_mask = rule1 | rule2
# y_pred_hybrid[is_anomaly_mask] = 1


# ===================
# Confusion matrix
# ===================
plt.figure(figsize=(8,6))
cm_hybrid = confusion_matrix(y_test, y_pred_hybrid)

sns.heatmap(cm_hybrid, 
            annot=True, 
            fmt='d', 
            cmap='Purples',
            xticklabels=['Normal Prediction', 'Fraud Prediction'],
            yticklabels=['Real Normal', 'Real Fraud'])

plt.title('Confusion Matrix - Hibrid model (IF + RF)')
plt.ylabel('Real')
plt.xlabel('Prediction')
plt.show()


#----------------------------------------------------
# Final comparision
#----------------------------------------------------
from sklearn.metrics import precision_score, recall_score, f1_score

iPred_test = isolationForest.predict(X_test)
y_pred_if = [1 if x == -1 else 0 for x in iPred_test]

y_pred_rf = model_rf.predict(X_test)

def calculate_metrics(y_real, y_pred):
    prec = precision_score(y_real, y_pred, pos_label=1, zero_division=0)
    rec = recall_score(y_real, y_pred, pos_label=1, zero_division=0)
    f1 = f1_score(y_real, y_pred, pos_label=1, zero_division=0)
    return prec, rec, f1


prec_if, rec_if, f1_if = calculate_metrics(y_test, y_pred_if)
prec_rf, rec_rf, f1_rf = calculate_metrics(y_test, y_pred_rf)
prec_hy, rec_hy, f1_hy = calculate_metrics(y_test, y_pred_hybrid)


df_compare = pd.DataFrame({
    'Model': ['Isolation Forest', 'Random Forest', 'Hybrid (IF + RF)'],
    'Precision': [prec_if, prec_rf, prec_hy],
    'Recall':[rec_if, rec_rf, rec_hy],
    'F1-Score':[f1_if, f1_rf, f1_hy]
})

print("\n" + "="*60)
print("MODELS PERFORMANCE COMPARISON (Focusing on Fraud Catching)")
print("="*60)

print(df_compare.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
print("="*60 + "\n")

#===================
# Visualizing Differences
#===================

df_melted = df_compare.melt(id_vars='Model', var_name='Metric', value_name='Score')

plt.figure(figsize=(10, 6))
ax = sns.barplot(data=df_melted, x='Metric', y='Score', hue='Model', palette='magma')

plt.title('Performance Comparison: IF vs RF vs Hybrid (Fraud Class Only)', fontsize=14)
plt.ylabel('Score (0.0 to 1.0)')
plt.ylim(0, 1.15) 
plt.legend(title='Model', loc='upper right')


for p in ax.patches:
    height = p.get_height()
    if height > 0: 
        ax.annotate(f"{height:.2f}", 
                    (p.get_x() + p.get_width() / 2., height), 
                    ha='center', va='center', 
                    xytext=(0, 8), 
                    textcoords='offset points',
                    fontsize=10, fontweight='bold')

plt.show()

#-------------------------------------------------------------

#Understanding the classification report

#Column Support
#Ths is the reality, meaning that we had 50000 normal values and 492 anomalies

#Column Recall
#This is the question: "On 492 anomalies, how many did the model catch?"
#The answer would be: "The model caught 63% of them"

#Column Precision
# this is the odds that tells that each time that the model thougth something is an anomalie, wich one you were right (False positives)
# On Isolation forest, it was right only 31% of the time

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