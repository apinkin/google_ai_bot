    import java.util.*;
    import java.io.*;
    import java.net.*;

    public class TCP {

       public static void main(String args[]) {
          // Check the command-line arguments.
          if (args.length < 5) {
              System.err.println("ERROR: wrong number of command-line arguments.");
              System.err.println("USAGE: TCP2 ip port username bot");
              System.exit(1);
          }

          // Get the server info
          int port = Integer.parseInt(args[1]);
          String ip = args[0];

          Socket sock = null;
          BufferedReader sockReader = null;
          PrintWriter sockWriter = null;

          // Perform the connection and get the read/write streams
          try {
             sock = new Socket(ip, port);
             sockReader = new BufferedReader(new InputStreamReader(sock.getInputStream()));
             sockWriter = new PrintWriter(sock.getOutputStream(), true);
          }
          catch(UnknownHostException e) {
             System.err.println("ERROR: unable to determine the server IP address");
             System.exit(1);
          }
          catch(Exception e) {
             System.err.println("ERROR: error on server connection");
             System.err.println(e.getMessage());
             System.exit(1);
          }

          // Get the bot command line
          String command = args[3];

          // Start the bot
          Process bot = null;
          BufferedReader botReader = null;
          PrintWriter botWriter = null;

          try {
             bot = Runtime.getRuntime().exec(command);
             botReader = new BufferedReader(new InputStreamReader(bot.getInputStream()));
             botWriter = new PrintWriter(bot.getOutputStream(), true);
          } catch (Exception e) {
             System.err.println("ERROR: failed to start bot");
             System.err.println(e.getMessage());
             System.exit(1);
          }

          // Tell the server we want play
          sockWriter.println("USER " + args[2]);

          // Basic stats data
          int turns = 0;
          boolean win = false;
          String enemy = "unknown";

          String line;
          StringBuilder message = new StringBuilder();
          try {
             // While the server data is valid
             while((line = sockReader.readLine()) != null) {
                if(line.startsWith("INFO")) {
                   System.out.println(line);
                }
                else if(line.startsWith("go")) {
                   // Add the GO command to the message
                   message.append("go\n");

                   // Send the turn data to bot
                   botWriter.println(message.toString());
                   message = new StringBuilder();

                   // Get the bot response
                   while(!(line = botReader.readLine()).startsWith("go")) {
                      message.append(line).append("\n");
                   }

                   // Add the GO command to the message
                   message.append("go\n");

                   // Perform bot actions
                   sockWriter.println(message.toString());
                   message = new StringBuilder();

                   // Collect turn data [statistics]
                   turns++;
                }
                else {
                   message.append(line).append("\n");
                }
             }
          } catch (Exception e) {
             System.err.println("ERROR: unknown exception");
             System.err.println(e.getMessage());
          }

          // TODO: collect the enemy name, win/lose stats
          //System.out.println(enemy + "|" + win + "|" + turns);
       }
    }
