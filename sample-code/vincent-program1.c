/* This code is an updated version of the sample code from "Computer Networks: A Systems
 * Approach," 5th Edition by Larry L. Peterson and Bruce S. Davis. Some code comes from
 * man pages, mostly getaddrinfo(3). */
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <string.h>
#include <unistd.h>

#define HOST "www.ecst.csuchico.edu"
#define SERVER_PORT "80"
#define REQUEST "GET /~kkredo/file.html HTTP/1.0\r\n\r\n"
#define TAG "<h1>"

/*
 * Lookup a host IP address and connect to it using service. Arguments match the first two
 * arguments to getaddrinfo(3).
 *
 * Returns a connected socket descriptor or -1 on error. Caller is responsible for closing
 * the returned socket.
 */
int lookup_and_connect( const char *host, const char *service );

int main( int argc, char *argv[] ) {
	int chunk_size;
	if ( argc == 2 ) {
		chunk_size = atoi(argv[1]);
	}
	else {
		fprintf( stderr, "usage: %s chunk size\n", argv[0] );
		exit( 1 );
	}

	/*
	// Ensure proper usage with a command-line argument
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <chunk size>\n", argv[0]);
        exit(EXIT_FAILURE);
    }
	*/

    // Parse and validate chunk size
    if (chunk_size < 5 || chunk_size > 1000) {
        fprintf(stderr, "Chunk size must be between 5 and 1000 bytes.\n");
        exit(EXIT_FAILURE);
    }
	

	/* Lookup IP and connect to server */
	int s;
	if ( ( s = lookup_and_connect( HOST, SERVER_PORT ) ) < 0 ) {
		exit( 1 );
	}

	send(s, REQUEST, strlen(REQUEST), 0); // sends the GET request to the server

	char buf[chunk_size + 1];
	int h1Total = 0;
	int byteTotal = 0;
	char *chunkptr;
	int len;
	while ((len = recv(s, buf, chunk_size, 0)) > 0) {
		// we'll want to do the processing of the data in here
		// aka the <h1> checking
		// we shouldn't use a for loop
		// we should use a library function or system call
		// the data sent from the HTML server are ascii
		// we should perform a string search
		// apparently the strstr function could work for this
		// strstr finds a substring within another string
		
		buf[len] = '\0';  // Null-terminate the received data
		
		/*
		if (len < chunk_size) {
			buf[len] = '\0';
		}
		else {
			buf[chunk_size - 1] = '\0';  // Prevent overflow
		}
		*/

		chunkptr = buf;
		while ((chunkptr = strstr(chunkptr, TAG)) != NULL) {
			h1Total++;
			chunkptr += 4; // IDE includes the null terminator. It is actually 4 long
			// moves to the next part of the chunk after the found string
		}
		byteTotal += len;
		// memset(buf, 0, chunk_size);
		// len gets the bytes received in the recv call per loop
		// so adding it each loop should give us the total bytes
	}
	close( s );

	printf("The total <h1> tags was: %d\n", h1Total);
	printf("The total bytes from the file was: %d\n", byteTotal);
	// -------------------------------------------------------------------------------
	// -------------------------------------------------------------------------------
	// -------------------------------------------------------------------------------

	
	return 0;
}

int lookup_and_connect( const char *host, const char *service ) {
	struct addrinfo hints;
	struct addrinfo *rp, *result;
	int s;

	/* Translate host name into peer's IP address */
	memset( &hints, 0, sizeof( hints ) );
	hints.ai_family = AF_UNSPEC; // would've needed to be changed to AF_UNSPEC
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
