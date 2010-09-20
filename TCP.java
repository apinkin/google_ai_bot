    import java.io.*;
    import java.net.*;

    public class TCP {
        public static boolean showLog = true;
        public static boolean showTimeTaken = true;
        public static boolean showTurns = true;

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
                sockReader = new BufferedReader(new InputStreamReader(sock.getInputStream()), 8192 * 32);
                sockWriter = new PrintWriter(new BufferedOutputStream(sock.getOutputStream(), 8192 * 32), true);
            }
            catch (UnknownHostException e) {
                System.err.println("ERROR: unable to determine the server IP address");
                System.exit(1);
            }
            catch (Exception e) {
                System.err.println("ERROR: error on server connection");
                System.err.println(e.getMessage());
                System.exit(1);
            }

            // Get the bot command line
            String command = args[3];

            // Start the bot
            Process bot;
            BufferedReader botReader;
            PrintWriter botWriter;

            try {
                bot = Runtime.getRuntime().exec(command);
                botReader = new BufferedReader(new InputStreamReader(bot.getInputStream()));
                botWriter = new PrintWriter(bot.getOutputStream(), true);
            } catch (Exception e) {
                System.err.println("ERROR: failed to start bot");
                System.err.println(e.getMessage());
                System.exit(1);
                return;
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
                while ((line = sockReader.readLine()) != null) {
                    if (showLog) {
                        System.err.println("From server: " + line);
                    }
                    if (line.startsWith("INFO")) {
                        System.out.println(line);
                    } else if (line.startsWith("go")) {
                        // Add the GO command to the message
                        message.append("go\n");
                        //logWriter.append("go\n");

                        // Send the turn data to bot
                        long t0 = showTimeTaken ? System.currentTimeMillis() : 0;
                        botWriter.println(message.toString());
                        StringBuilder botResponce = new StringBuilder();
                        // Get the bot response
                        while (!(line = botReader.readLine()).startsWith("go")) {
                            botResponce.append(line).append("\n");
                            if (showLog) {
                                System.err.println("To server: " + line);
                            }
                            //logWriter.append(line).append("\n");
                        }

                        // Add the GO command to the message
                        botResponce.append("go\n");
                        if (showLog) {
                            System.err.println("To server: " + "go\n");
                        }
                        if (showTimeTaken) {
                            long t1 = System.currentTimeMillis();
                            System.err.println("Turn " + turns + " taken " + (t1 - t0) + " ms");
                        }

                        // Perform bot actions
                        sockWriter.println(botResponce.toString());
                        sockWriter.flush();
                        message = new StringBuilder();

                        // Collect turn data [statistics]
                        turns++;
                        if (showTurns) {
                            System.err.println("NEW TURN " + turns);
                        }
                    } else {
                        message.append(line).append("\n");
                    }
                }
            } catch (Exception e) {
                System.err.println("ERROR: unknown exception");
                System.err.println(e.getMessage());
            }

            bot.destroy();

            // TODO: collect the enemy name, win/lose stats
            //System.out.println(enemy + "|" + win + "|" + turns);
        }
    }
