# Архитектура LEGACY 7

Роли: participant, jury, organizer, admin. Права проверяются на backend.

Модели: User, Profile, Category, Contest, Prize, JudgingCriterion, ContestJury,
Submission, Evaluation, EvaluationScore, Notification, Favorite, LeaderboardEntry.

API: /api/v1/ — auth, contests, submissions, judging, leaderboard, notifications.

Рейтинг считается на сервере по подтверждённым оценкам жюри.