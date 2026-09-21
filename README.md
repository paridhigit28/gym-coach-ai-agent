URL- https://gym-coach-ai-agent.onrender.com

Trainora — AI-Powered Personal Fitness Coach

Trainora is an AI-powered fitness platform built with **Streamlit** that combines personalized nutrition planning, workout planning, and real-time AI-assisted workout coaching in a single application.

The platform uses a user's fitness assessment, goals, activity level, dietary preferences, restrictions, and workout requirements to provide personalized fitness guidance.


Features

AI Diet Planner

Generates personalized meal plans based on the user's:

- Age
- Gender
- Height and weight
- Fitness goal
- Activity level
- Target weight
- Workout schedule
- Medical conditions
- Food restrictions and allergies
- Diet preference
- Cuisine preference
- Body build

The nutrition system includes:

- BMI calculation
- Calorie and nutrition calculations
- Food database integration
- Macro-aware meal planning
- Food image mapping
- Nutrition verification
- Personalized meal recommendations

AI Workout Planner

Creates personalized workout plans based on the user's fitness assessment.

The planner considers:

- Fitness level
- Workout experience
- Fitness goal
- Workout days per week
- Workout duration
- Equipment availability
- Activity level

The application includes exercise support for movements such as:

- Squats
- Push-ups
- Lunges
- Biceps curls
- Shoulder presses

and other exercises supported by the exercise database.

Live AI Gym Coach

Trainora includes a real-time workout coaching module using the device camera.

The Live AI Gym Coach provides:

- Real-time pose detection
- Exercise tracking
- Rep counting
- Set tracking
- Workout session tracking
- Form-related feedback
- AI-generated coaching instructions
- Voice-based coaching

The pose-tracking system uses **MediaPipe Pose Landmarker** and OpenCV.

The application also includes a guided mode for exercises where dedicated pose detection is not available.


AI Architecture

Trainora is organized around three major AI-driven components:


                    ┌─────────────────────┐
                    │       Trainora      │
                    │   Fitness Platform  │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
     ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
     │ AI Diet      │  │ AI Workout   │  │ Live AI Gym     │
     │ Planner      │  │ Planner      │  │ Coach           │
     └──────┬───────┘  └──────┬───────┘  └────────┬────────┘
            │                 │                    │
            ▼                 ▼                    ▼
     Nutrition Engine   Workout Logic       MediaPipe Pose
            │                 │                    │
            └────────────┬────┴────────────┬───────┘
                         │                 │
                         ▼                 ▼
                   Groq LLM            SQLite /
                                      SQLAlchemy
