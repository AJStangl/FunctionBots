function RunBot {
    conda activate reddit-function-bot
    func start --functions generate -p 7074
}

$a = 1
$b = 1

Do {
  RunBot
} while($a == $b)