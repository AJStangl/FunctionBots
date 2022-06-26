function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-submit-post --verbose --port 7081
}

while(1) {
    RunBot
}