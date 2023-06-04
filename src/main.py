#!/usr/bin/env python3

import math
import matplotlib.pyplot as plt
import numpy as np
import keyboard
import random
import rospy
import tf
from fiducial_msgs.msg import FiducialTransformArray
from initialization import initialize_state_covariance
from motion import update_pose
from update import initialize_landmark
from convariance import jacobian, covariance 
from nav_msgs.msg import Odometry

num_landmarks=32
Rt=0.05

k=0

Fx = np.zeros((3, 2*num_landmarks + 3))
for i in range(3):
    Fx[i,i] = 1
    
# Constants for the interface dimensions
WIDTH = 30
HEIGHT = 15

previous_time=0
start_time=0
position_x=position_y=0
list_index = []

# Variables for particle position, heading, and speed
particle_x = WIDTH // 2
particle_y = HEIGHT // 2
particle_heading = 0  # In degrees, 0 degrees is facing right
particle_speed = 10
angular_speed = 10


# Variables to store distances
distances = []



#Initialize the state vetor and the convariance matrix
state_vector, covariance_matrix = initialize_state_covariance(num_landmarks)

print("State Vector:")
print(state_vector)

print("Covariance Matrix:")
print(covariance_matrix)

LANDMARKS = []
for _ in range(num_landmarks):
    landmark_x = random.randint(0, WIDTH)
    landmark_y = random.randint(0, HEIGHT)
    LANDMARKS.append((landmark_x, landmark_y))


# Create the figure and axis for the graph
fig, ax = plt.subplots()

# Function to calculate the Euclidean distance between two points
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

# Function to update the distance between the particle and landmarks
def update_distances():
    distances.clear()
    for landmark in LANDMARKS:
        distance = calculate_distance(particle_x, particle_y, landmark[0], landmark[1])
        distances.append(distance)

# Function to update the particle's position based on its heading and speed
def update_position():
    global particle_x, particle_y, particle_heading  # Declare as global to modify the global variables
    angle = math.radians(particle_heading)
    delta_x = particle_speed * math.cos(angle)
    delta_y = particle_speed * math.sin(angle)
    particle_x += int(delta_x)
    particle_y += int(delta_y)
    
def callback(msg):
    global previous_time
    global state_vector
    global start_time
    global position_x, position_y
    global covariance_matrix
    
    #rospy.loginfo("Received message: %s", msg.pose.pose)

    #rospy.loginfo("current time: %s.%s", msg.header.stamp.secs, msg.header.stamp.nsecs)

    orientation_x = msg.pose.pose.orientation.x
    orientation_y = msg.pose.pose.orientation.y
    orientation_z = msg.pose.pose.orientation.z
    orientation_w = msg.pose.pose.orientation.w
    
    position_x = msg.pose.pose.position.x
    position_y = msg.pose.pose.position.y

    velocity = msg.twist.twist.linear.x
    angular_velocity = msg.twist.twist.angular.z

     # Access the seconds and nanoseconds components of the timestamp
    timestamp_secs = msg.header.stamp.secs
    timestamp_nsecs = msg.header.stamp.nsecs

    time = float(str(timestamp_secs) + '.' + str(timestamp_nsecs).zfill(9))
    if previous_time == 0:
        previous_time=time
        dt=0
    else:
        dt=time-previous_time
        
        previous_time=time
        
    if start_time == 0:
        start_time=time

    elapsed_time=time-start_time
    
    # Convert the orientation data to Euler angles     
    quarternion = (orientation_x, orientation_y, orientation_z, orientation_w)
    euler = tf.transformations.euler_from_quaternion(quarternion)
        
    # Extract roll, pitch, and yaw from Euler angles
    roll = euler[0]
    pitch = euler[1]
    yaw = euler[2]
        
     # Set the flag to indicate new data arrival
    new_data_flag = True

    """ print("tempo: \n", dt, "angulo: \n", yaw)
    print("Velocity: ",velocity, "Angular Velocity: ",angular_velocity,"\n") """
    #Running the motion model

    Gt = jacobian(velocity, angular_velocity, dt, state_vector[2,0], Fx, num_landmarks)
    covariance_matrix =  covariance(Gt,covariance_matrix,Fx,Rt,num_landmarks)

    state_vector = update_pose(state_vector,Fx, dt, velocity, num_landmarks, angular_velocity)

    #print("state_vector: \n", state_vector)

    return new_data_flag

def callback_fiducial(msg):
    obtain_fiducial_values(msg)


def obtain_fiducial_values(msg):
    global list_index
    global state_vector

    i=0

    instance_id = set()

    z_matrix=np.empty((2,0))

    for transform in msg.transforms:
        i=i+1

        #obtain the distance values
        landmark_x=transform.transform.translation.x
        landmark_y=transform.transform.translation.y
        landmark_z=transform.transform.translation.z

        #calculate the R distance, the distance from the robot to the landmark in the 3D axis
        distance_R=math.sqrt(landmark_x**2+landmark_y**2+landmark_z**2)

        #obtain the quarternion values
        rotation_x = transform.transform.rotation.x
        rotation_y = transform.transform.rotation.y
        rotation_z = transform.transform.rotation.z
        rotation_w = transform.transform.rotation.w

        # Convert the orientation data to Euler angles     
        quarternion = (rotation_x, rotation_y, rotation_z, rotation_w)
        euler = tf.transformations.euler_from_quaternion(quarternion)

        observe_z = np.array([distance_R, euler[2]]).reshape(2, 1)

        z_matrix=np.concatenate((z_matrix,observe_z), axis=1)
        
        marker_id = transform.fiducial_id

        #nova landmark no header
        if marker_id not in instance_id:
            instance_id.add(marker_id)

        global k
        #Se a landmark nunca foi observada
        if marker_id not in list_index:
            # Register the new ID
            #observed_ids.append(marker_id)
            index=k
            k+=1
            list_index.append(marker_id)

            print("number of ids: ", k)
            print("landmark array: ", list_index)

            rospy.loginfo("New marker ID registered: {}".format(marker_id))
            
            state_vector[2 * index + 3, 0] = state_vector[0, 0] + observe_z[0, 0] * math.cos(observe_z[1][0] + state_vector[2, 0])
            state_vector[2 * index + 4, 0] = state_vector[1, 0] + observe_z[0, 0] * math.cos(observe_z[1][0] + state_vector[2, 0])

            

    """ for j in range(i):
        id = instance_id(j)

        MUDAR SET PARA LISTA!!!!
        
        index=observed_ids.index(id)
        data = [row[0] for row in z_matrix]

        covariance_matrix , state_vector = initialize_landmark(index, num_landmarks, covariance_matrix, state_vector, data) """


    

# Initialize the ROS node
rospy.init_node('subscriber_node')
new_data_flag = False
# Create a Subscriber object
sub = rospy.Subscriber('/pose', Odometry, callback) 

sub2 = rospy.Subscriber('/fiducial_transforms', FiducialTransformArray, callback_fiducial)

# Main loop
while True:
    # Update distances
    update_distances()
    
    if new_data_flag:
        # New data is available, perform necessary operations
        # Reset the flag
        print("testing")
        new_data_flag = False

 
    # Print distances
    #print("Distances to landmarks:")
    #for i, distance in enumerate(distances):
        #print(f"Landmark {i+1}: {distance:.2f}") 


    # Clear the previous plot
    #ax.clear()

    # Plot the particle position
    #ax.plot(particle_x, particle_y, 'ro', label='Particle')

    # Plot the landmark positions
    #for i, landmark in enumerate(LANDMARKS):
        #ax.plot(landmark[0], landmark[1], 'bo', label=f'Landmark {i+1}')
        
    print("State Vector:", state_vector)
    
    ax.plot(state_vector[0], state_vector[1], 'go', markersize=1)
    
    for i in range(num_landmarks):
        if state_vector[2*i+3] != 0 or state_vector[2*i+4] != 0:
            ax.plot(state_vector[2*i+3], state_vector[2*i+4], 'r+',markersize = 3)


    ax.plot(position_x, position_y, 'bo', markersize=1)
    
    # Set the axis limits
    ax.set_xlim(-WIDTH, WIDTH)
    ax.set_ylim(-HEIGHT, HEIGHT*2)

    # Set the title and labels
    ax.set_title('Active Particle')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')

    # Update the legend
    ax.legend()

    # Display the plot
    plt.pause(0.01)

    # Read keyboard input
    """ if keyboard.is_pressed('up'):
        update_position()
    elif keyboard.is_pressed('left'):
        particle_heading += angular_speed
    elif keyboard.is_pressed('right'):
        particle_heading -= angular_speed
    elif keyboard.is_pressed('x'):
            particle_speed += 1
    elif keyboard.is_pressed('z'):
            particle_speed -= 1
            print("particle speed:", particle_speed)
    elif keyboard.is_pressed('s'):
            angular_speed += 1
    elif keyboard.is_pressed('a'):
            angular_speed -= 1
    elif keyboard.is_pressed('q'):
        break  # Exit the program if 'q' key is pressed """

    # Limit particle position within the interface dimensions
    particle_x = max(0, min(WIDTH - 1, particle_x))
    particle_y = max(0, min(HEIGHT - 1, particle_y))

# Close the plot window
plt.close(fig)
