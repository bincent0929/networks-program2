#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <string.h>
#include <unistd.h>

#define SERVER_PORT "5432"
#define MAX_LINE 256

/*
 * Lookup a host IP address and connect to it using service. Arguments match the first two
 * arguments to getaddrinfo(3).
 *
 * Returns a connected socket descriptor or -1 on error. Caller is responsible for closing
 * the returned socket.
 */
int lookup_and_connect( const char *host, const char *service );
void join();
void publish();
void search();

int main( int argc, char *argv[] ) {
	char *host;
	char buf[MAX_LINE];
	int s;
	int len;
    char yesOrNo;

	if ( argc == 2 ) {
		host = argv[1];
	}
	else {
		fprintf( stderr, "usage: %s host\n", argv[0] );
		exit( 1 );
	}

	/* Lookup IP and connect to server */
	if ( ( s = lookup_and_connect( host, SERVER_PORT ) ) < 0 ) {
		exit( 1 );
	}

    printf("Are you done with the program? (y/n): \n");
    scanf("%c", yesOrNo);
    if (yesOrNo == 'y') {
        close( s );
        return 0;
    }
    while (1) {
        printf("Do you want to join a peer?: \n");
        scanf("%c", yesOrNo);
        if (yesOrNo == 'y') {
            join();
            printf("Do you want to publish your info?: \n");
            scanf("%c", yesOrNo);
            if (yesOrNo == 'y') {
                publish();
                printf("Do you want to search?: \n");
                scanf("%c", yesOrNo);
                if (yesOrNo == 'y') {
                    search();
                    break;
                }
                else {
                    break;
                }
            }
            else {
                printf("Do you want to search?: \n");
                scanf("%c", yesOrNo);
                if (yesOrNo == 'y') {
                    search();
                }
                else {
                    break;
                }
            }
        }
        else {
            printf("Do you want to publish your info?: \n");
            scanf("%c", yesOrNo);
            if (yesOrNo == 'y') {
                publish();
                printf("Do you want to search?: \n");
                scanf("%c", yesOrNo);
                if (yesOrNo == 'y') {
                    search();
                    break;
                }
                else {
                    break;
                }
            }
            else {
                printf("Do you want to search?: \n");
                scanf("%c", yesOrNo);
                if (yesOrNo == 'y') {
                    search();
                }
                else {
                    break;
                }
            }
        }

        printf("Are you done with the program? (y/n): \n");
        scanf("%c", yesOrNo);
        if (yesOrNo == 'y') {
            close( s );
            return 0;
        }
    }
}

/**********************************************
 * sends the action number and peer ID to the receiver
**********************************************/
void join() {

}

/**********************************************
 * opens, read, then counts the "SharedFiles"
 * then sends to the receiver (htonl?)
**********************************************/
void publish() {

}

/**********************************************
 * prepares the query to send to the receiver
 * then receives the query from the other machine
 * extracts the ID, IP, and Port#
 * then goes back and asks if exiting
**********************************************/
void search() {


}

int lookup_and_connect( const char *host, const char *service ) {
	struct addrinfo hints;
	struct addrinfo *rp, *result;
	int s;

	/* Translate host name into peer's IP address */
	memset( &hints, 0, sizeof( hints ) );
	hints.ai_family = AF_INET;
	hints.ai_socktype = SOCK_STREAM;
	hints.ai_flags = 0;
	hints.ai_protocol = 0;

	if ( ( s = getaddrinfo( host, service, &hints, &result ) ) != 0 ) {
		fprintf( stderr, "stream-talk-client: getaddrinfo: %s\n", gai_strerror( s ) );
		return -1;
	}

	/* Iterate through the address list and try to connect */
	for ( rp = result; rp != NULL; rp = rp->ai_next ) {
		if ( ( s = socket( rp->ai_family, rp->ai_socktype, rp->ai_protocol ) ) == -1 ) {
			continue;
		}

		if ( connect( s, rp->ai_addr, rp->ai_addrlen ) != -1 ) {
			break;
		}

		close( s );
	}
	if ( rp == NULL ) {
		perror( "stream-talk-client: connect" );
		return -1;
	}
	freeaddrinfo( result );

	return s;
}
