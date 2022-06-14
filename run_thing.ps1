function RunBot
{
    conda activate reddit-function-bot
    func start --functions function-timer-table-collection  --port 7081
}

while(1) {
    RunBot
}