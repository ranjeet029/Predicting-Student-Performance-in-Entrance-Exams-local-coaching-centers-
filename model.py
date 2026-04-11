import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import RandomForestClassifier

data=pd.read_csv("datasets/students_dataset.csv")
data.columns = data.columns.str.lower()

X = data[['maths','physics','chemistry','biology','attendance','practice']]
y = data['total']

reg_model=RandomForestRegressor()

reg_model.fit(X,y)

data['performance']=data['total'].apply(
lambda x: "Excellent" if x>300 else
("Average" if x>220 else "Weak")
)

clf_model=RandomForestClassifier()

clf_model.fit(X,data['performance'])

def predict_student(m,p,c,b,a,pr):

    score=reg_model.predict([[m,p,c,b,a,pr]])

    category=clf_model.predict([[m,p,c,b,a,pr]])

    importance=reg_model.feature_importances_

    return score[0],category[0],importance