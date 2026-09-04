from flask import Flask, request, render_template
from planner import generate_plan
from validation import parse_plan_form

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        try:
            subjects, hours = parse_plan_form(request.form)
            plan = generate_plan(subjects, hours)
        except ValueError as error:
            return render_template("index.html", error=str(error)), 400

        return render_template("index.html", plan=plan)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=False)
