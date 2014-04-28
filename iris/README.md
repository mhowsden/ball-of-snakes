iris
====

*A minimalist file retreiver*

To use this you'll need to edit _run.bash and _config and rename them to run.bash and config.

Iris is composed of three components:

 1. the main web interface that allows a user to specify a file to download for later and puts it in
the queue
 2. a script that's running via crontab on the server which checks the db to see if a new file has been queued and downloads it. it needs to:
    * check to make sure the file at the url exists and stores the size of the file in the db
    * check the local filesystem to make sure it has enough room for the file (and plenty to spare)
    * pulls down the file via wget but likely also has to support resume in case an early download choked
    * writes out failures and states to a log file
 3. a script that runs locally that syncs the remote filesystem where the files are being stored to a local
 filesystem and deletes the files from the remote server
