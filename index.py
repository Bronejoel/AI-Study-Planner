from flask import Flask, request, render_template
from planner import generate_plan

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        subjects = []

        names = request.form.getlist("name")
        difficulties = request.form.getlist("difficulty")
        days = request.form.getlist("days")

        for i in range(len(names)):
            if names[i] and difficulties[i] and days[i]:
                subjects.append({
                    "name": names[i],
                    "difficulty": int(difficulties[i]),
                    "days_left": int(days[i])
                })

        hours = int(request.form["hours"])

        plan = generate_plan(subjects, hours)

        return render_template("index.html", plan=plan)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)