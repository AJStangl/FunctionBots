function RunBot
{
    conda activate reddit-function-bot
    func start --functions gen --port 7073
}

$a = 1
$b = 1

Do {
  RunBot
} while($a == $b)
