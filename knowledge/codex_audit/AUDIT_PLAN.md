# Auditplan

Bevroren scope: infrastructuur, agents, hourly, bridge, weather/TWC, point-in-time, holdout, execution, tests, security en Git-historie. Eerst baseline; daarna veilige falsificatie met fixtures; geen productieactivering, trading, betaalde diensten of push. Geen reparatie vóór lokale baselinecommit. Tweede adversariële review en eindrapport verplicht.

Review: vroeg goedkope reproducties; geen tests versoepelen; geen fill-aannames; venue-onafhankelijke conclusies; bron- en klokprovenance expliciet controleren.

Blokkade: .git is read-only. worktree/branch-aanmaak en gedeelde coordinator falen. Geen uitbreiding rechten gevraagd. Auditdocumentatie wordt binnen toegestane workspace opgeslagen; productiecode blijft ongewijzigd zolang baseline niet gecommit kan worden.
