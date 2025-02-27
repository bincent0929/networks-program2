/**
 * Group Members: Vincent Roberson and Muhammad I Sohail
 * ECEE 446 Section 1
 * Spring 2025
 */
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
/**
 * sends the join request to the registry to join the network
 * only needs to happen once per program run
 * sends a 1 byte field of 0, then a 4 byte peer ID
 * The peer ID must be in network byte order
 * each peer ID must be unique and 
 * is provided by a command line argument
*/
void join();
/**
 * Informs the registry of what files are available to share
 * opens, read, then counts the files in the "SharedFiles" directory
 * any files in the directory are then added to the registry index
 * 1 byte for action = 1, 4 bytes for the file count, variable bytes of null terminated for the file names
 * must contain Count file names in total with exactly NULL characters
 * Count must be in network byte order
 * each filename is at most 100 bytes (including NULL)
 * no unused bytes between filenames
 * a publish cannot be larger than 1200 bytes (12 files)
*/
void publish();
/**
 * look for peers with a desired filename
 * a request with the name of the file is sent from the peer
 * the registry sends a search response after it receives a search request
 * the response indicates that another peer has the file requested
 * if the peer is looking for a file published by the peer, it won't locate it
 * a search request has 1 byte containing 2, then variable bytes for the desired null-terminated filename
 * a search response (sent from the registry to the requesting peer) contains
 * 4 bytes for a peer ID, 4 bytes for an IPv4 address, and 2 bytes for a peer port
 * if the file is not found, then the response will contain zeros (or if the peer themself has the file)
 * user inputs the name of the file on a newline after SEARCH is entered
*/
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


}

void join() {

}

void publish() {

}

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
