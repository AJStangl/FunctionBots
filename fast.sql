SELECT
    "Id", "RedditId", "TextGenerationPrompt"
INTO TEMPORARY TABLE  populated_table
FROM
    "BotTracking"
WHERE
    "TextGenerationPrompt" != '';

UPDATE "BotTracking"
SET "TextGenerationPrompt" = "BotTracking"."TextGenerationPrompt"
FROM "BotTracking" t2
join populated_table t1 on t1."RedditId" = t2."RedditId"
WHERE t1."TextGenerationPrompt" != ''
and t2."TextGenerationPrompt" <> t1."TextGenerationPrompt";

drop table populated_table;