import pandas as pd
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import RandomForestClassifier

# dataset path
DATA_PATH = "datasets/students_dataset.csv"

reg_model = None
clf_model = None


def load_and_train():

    global reg_model, clf_model

    if not os.path.exists(DATA_PATH):
        print("Dataset not found. Model not trained.")
        return

    data = pd.read_csv(DATA_PATH)

    data.columns = data.columns.str.lower().str.strip()

    # required columns check
    required_cols = ['maths','physics','chemistry','biology','attendance','practice','total']
    
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"Missing column in dataset: {col}")

    X = data[['maths','physics','chemistry','biology','attendance','practice']]
    y = data['total']

    # Regression Model
    reg_model = RandomForestRegressor()
    reg_model.fit(X,y)

    # Performance category
    data['performance'] = data['total'].apply(
        lambda x: "Excellent" if x > 300 else
        ("Average" if x > 220 else "Weak")
    )

    # Classification Model
    clf_model = RandomForestClassifier()
    clf_model.fit(X, data['performance'])


def predict_student(m,p,c,b,a,pr):

    global reg_model, clf_model

    # model train if not loaded
    if reg_model is None or clf_model is None:
        load_and_train()

    if reg_model is None:
        return 0,"Dataset Missing",[0,0,0,0,0,0]

    score = reg_model.predict([[m,p,c,b,a,pr]])

    category = clf_model.predict([[m,p,c,b,a,pr]])

    importance = reg_model.feature_importances_

    return score[0], category[0], importance.tolist()