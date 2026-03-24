// 测试用例21: 深度嵌套spawn
// 测试多层嵌套的spawn创建的线程之间的竞争

main() {
    var counter: Int64 = 0
    
    // 第一层spawn
    spawn {
        counter = counter + 1  // 写操作
        
        // 第二层spawn
        spawn {
            counter = counter + 1  // 写操作
            
            // 第三层spawn
            spawn {
                counter = counter + 1  // 写操作，与所有外层竞争
            }
        }
    }
    
    // 另一个独立的spawn
    spawn {
        counter = counter + 1  // 写操作
    }
    
    println(counter)
}